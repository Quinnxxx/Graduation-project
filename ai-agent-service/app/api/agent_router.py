"""对外 AI 对话路由（business-service 转发专用）。

提供两个对话入口，均通过 ``X-Internal-Token`` 内部令牌校验，仅允许
business-service 转发层调用，防止 AI 接口被公网直接访问：

- ``POST /agent/chat``：非流式，走 LangGraph 图 ``ainvoke`` 完整编排，
  一次性返回完整结果（适合内部批处理 / 非实时调用）；
- ``POST /agent/chat/stream``：SSE 流式，走图构建器 ``run_stream`` 生成器，
  以 ``meta / chunk / final / error`` 事件逐 token 推送（适合前端实时对话）。

user_id 由转发层从用户 JWT 解析后注入 :class:`ChatRequest`，AI 服务不直接
面向终端用户鉴权。
"""

import asyncio
import json
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from app.api.schemas import ApiResponse, ChatRequest
from app.config.settings import get_settings
from app.graph.builder import AgentGraphBuilder
from app.graph.state import AgentState

router = APIRouter(prefix="/api/v1", tags=["agent"])

# 意图 → 前端展示名（chat 兜底无 Agent 包名，按意图回退中文名）
_INTENT_DISPLAY_NAME = {
    "chat": "AI 助手",
    "job": "岗位匹配顾问",
    "resume": "简历优化专家",
    "tech": "技术面试官",
    "hr": "HR 面试官",
}


def _display_name(agent_name: str, intent: str) -> str:
    """取前端展示名：优先 agent_name，为空时按 intent 回退。

    Args:
        agent_name: 真实 Agent 节点写入的名称（job/resume/tech/hr）。
        intent: 路由意图（chat 兜底无 agent_name，需回退）。

    Returns:
        中文展示名。
    """
    if agent_name:
        return agent_name
    return _INTENT_DISPLAY_NAME.get(intent, intent or "")


async def _distill_review_background(
    builder: AgentGraphBuilder, user_id: str, query: str, response: str
) -> None:
    """后台异步执行复盘沉淀，任何异常仅告警不抛出。

    由 :mod:`asyncio.create_task` 调度，保证 handler 响应路径零额外延迟；
    进程关闭时未完成的后台任务可能丢弃（沉淀是增强能力，可接受）。
    """
    try:
        await builder.distill_review(user_id, query, response)
    except Exception as exc:  # noqa: BLE001 - 沉淀失败不阻断响应
        logger.warning("复盘沉淀后台任务异常: {}", exc)


async def _distill_dialogue_background(
    builder: AgentGraphBuilder,
    user_id: str,
    intent: str,
    query: str,
    response: str,
) -> None:
    """后台异步执行真实 Agent 对话沉淀（source=模拟面试/咨询对话），异常仅告警。"""
    try:
        await builder.distill_dialogue(user_id, intent, query, response)
    except Exception as exc:  # noqa: BLE001 - 沉淀失败不阻断响应
        logger.warning("对话沉淀后台任务异常: {}", exc)


def _trigger_stream_distill(
    builder: AgentGraphBuilder,
    user_id: str,
    intent: Optional[str],
    query: str,
    final_text: str,
) -> None:
    """流式沉淀入口：按场景选择后台任务，create_task 不 await 不阻塞。

    立项范围收紧为两类：
    1. 复盘类（intent=chat 且 query 命中复盘强短语）——与非流式桥接
       （:meth:`AgentGraphBuilder.distill_review`）；
    2. 真实 Agent 场景（job/resume/tech/hr）长响应（>200 字符由
       :meth:`AgentGraphBuilder.distill_dialogue` 内部判定）——
       tech/hr 沉淀为"模拟面试"、job/resume 沉淀为"咨询对话"。
    其余场景（普通自由问答）不沉淀；幂等由 _distilled_keys 场景前缀键 +
    user_memory.content_hash 唯一键共同保证。
    """
    if intent == "chat" and builder._is_review_query(query):
        coro = _distill_review_background(builder, user_id, query, final_text)
    elif intent in ("job", "resume", "tech", "hr"):
        coro = _distill_dialogue_background(
            builder, user_id, intent, query, final_text
        )
    else:
        return
    asyncio.create_task(coro)


def _verify_internal_token(request: Request) -> None:
    """校验内部访问令牌：``X-Internal-Token`` 必须与 AI_INTERNAL_TOKEN 一致。

    仅 business-service 转发层持有该令牌，防止 AI 对话接口被公网直接调用；
    校验失败返回 HTTP 401（非业务码，便于转发层做语义化处理）。

    Args:
        request: 请求对象（从中读取 X-Internal-Token 头）。

    Raises:
        HTTPException: 令牌缺失或不匹配时返回 401。
    """
    settings = get_settings()
    token = request.headers.get("X-Internal-Token", "")
    if token != settings.internal_token:
        raise HTTPException(status_code=401, detail="Invalid internal token")


def _build_state(req: ChatRequest) -> AgentState:
    """根据对话请求构造 AgentState（字段与图约定一致）。

    Args:
        req: 对话请求体。

    Returns:
        初始化后的 AgentState；resume_text 非空时一并注入。
    """
    state = AgentState(
        user_id=req.user_id,
        user_input=req.query,
        messages=[],
        intermediate_results={},
        tool_call_results=[],
        final_response="",
        error=None,
    )
    if req.resume_text:
        state["resume_text"] = req.resume_text
    if req.session_id:
        state["session_id"] = req.session_id
    return state


@router.post(
    "/agent/chat",
    dependencies=[Depends(_verify_internal_token)],
    response_model=ApiResponse[dict],
    summary="非流式 AI 对话",
)
async def agent_chat(req: ChatRequest, request: Request) -> ApiResponse[dict]:
    """非流式对话：走 LangGraph 图 ``ainvoke`` 完整编排。

    Args:
        req: 对话请求体。
        request: 请求对象（获取 lifespan 挂载的编译图）。

    Returns:
        ApiResponse，data 含 agent_name / intent / final_response / error。
    """
    graph = request.app.state.agent_graph
    builder = request.app.state.agent_builder
    state = _build_state(req)
    result = await graph.ainvoke(state)
    final_response = result.get("final_response", "")
    # 复盘后置沉淀：非流式 /agent/chat 是前端复盘报告的唯一入口（/chat/stream
    # 不做沉淀）。成功拿到响应后异步调用，不 await 阻塞响应路径（吞吐优先：
    # create_task 交给事件循环执行；风险是进程关闭时未完成任务可能丢弃，
    # 沉淀为增强能力，可接受）。失败由后台任务内部吞掉仅告警。
    if final_response:
        asyncio.create_task(
            _distill_review_background(
                builder, req.user_id, req.query, final_response
            )
        )
    return ApiResponse.ok(
        {
            "agent_name": _display_name(
                result.get("agent_name", ""), result.get("intent", "")
            ),
            "intent": result.get("intent", ""),
            "final_response": final_response,
            "error": result.get("error"),
        }
    )


@router.post(
    "/agent/chat/stream",
    dependencies=[Depends(_verify_internal_token)],
    summary="SSE 流式 AI 对话",
)
async def agent_chat_stream(
    req: ChatRequest, request: Request
) -> StreamingResponse:
    """SSE 流式对话：走图构建器 ``run_stream`` 组件化生成器。

    事件以 SSE ``data: {...}\\n\\n`` 帧推送，事件类型为
    meta / chunk / final / error。

    Args:
        req: 对话请求体。
        request: 请求对象（获取 lifespan 挂载的图构建器）。

    Returns:
        StreamingResponse（media_type=text/event-stream）。
    """
    builder = request.app.state.agent_builder
    state = _build_state(req)

    async def event_gen() -> AsyncIterator[str]:
        """将 run_stream 事件转换为 SSE 文本帧，并在 final 后触发流式沉淀。

        Yields:
            SSE 数据帧字符串。
        """
        # 流式沉淀追踪：meta 记录意图，final 记录完整文本
        intent: Optional[str] = None
        final_text = ""
        try:
            async for event in builder.run_stream(state):
                etype = event.get("type")
                if etype == "meta":
                    intent = (event.get("data") or {}).get("intent")
                    event["data"] = event.get("data") or {}
                    event["data"]["agent_name"] = _display_name("", intent)
                elif etype == "final":
                    final_text = str(event.get("data", "") or "")
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        except Exception as exc:  # noqa: BLE001 - 兜底转 error 事件，避免断流无提示
            logger.exception("流式执行异常: {}", exc)
            payload = json.dumps(
                {"type": "error", "data": "系统内部错误，请稍后再试"},
                ensure_ascii=False,
            )
            yield f"data: {payload}\n\n"
        # 流式沉淀：开关开启且 final 已产出时后台执行（create_task 不阻塞响应路径）
        if final_text and get_settings().memory_stream_distill:
            _trigger_stream_distill(
                builder, req.user_id, intent, req.query, final_text
            )

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # 关闭 Nginx 缓冲，保证 token 实时下发
            "X-Accel-Buffering": "no",
        },
    )
