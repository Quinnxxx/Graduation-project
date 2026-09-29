"""岗位分析 Agent。

根据用户求职意向，通过 :class:`SearchJobsTool` 查询 business-service 的真实
在招岗位库，再由大模型基于岗位数据输出人岗匹配分析、匹配点与投递建议。
Agent 名称 ``job`` 与 LangGraph 路由意图一致。

**双执行模式**：

1. **旧模式（同步，单次 LLM 调用）**：
   - :meth:`JobAgent.run`：同步执行，供 LangGraph 图批处理调用
   - :meth:`JobAgent.stream_run`：异步流式，供流式对话逐 token 输出
   - 两者共用 :meth:`JobAgent._build_prompt`，保证提示词与工具调用一致

2. **新模式（异步，ReAct 循环）**：
   - :meth:`JobAgent.arun`：ReAct 版本，LLM 自主调用工具
   - :meth:`JobAgent.astream_run`：ReAct 流式版本
   - 工具列表：search_jobs, knowledge_search, get_latest_ability, save_memory
"""

from typing import Any, List, Optional

from app.agents.base import BaseAgent
from app.config.settings import Settings
from app.graph.state import AgentState
from app.llm.factory import get_llm_factory
from app.services.business_client import BusinessServiceClient
from app.tools.lc import (
    GetLatestAbilityTool,
    KnowledgeSearchTool,
    SaveMemoryTool,
    SearchJobsTool,
)
from app.tools.search_jobs_tool import SearchJobsTool as LegacySearchJobsTool

# 单次送入大模型的最大岗位条数
_JOB_FETCH_SIZE = 10
# 岗位 JD 文本截断长度，避免提示词过长
_JOB_DESC_LIMIT = 80
# 携带的最近对话轮数
_HISTORY_LIMIT = 6


def _message_role(message: Any) -> str:
    """提取消息角色，兼容 dict 与 LangChain BaseMessage。

    Args:
        message: dict（含 role）或 LangChain 消息对象（含 type）。

    Returns:
        归一化后的角色名（user / assistant / system）。
    """
    if isinstance(message, dict):
        return message.get("role", "user")
    raw = getattr(message, "type", None) or getattr(message, "role", "user")
    return {"human": "user", "ai": "assistant", "system": "system"}.get(raw, raw)


def _message_content(message: Any) -> str:
    """提取消息文本，兼容 dict 与 LangChain BaseMessage。

    Args:
        message: dict（含 content）或 LangChain 消息对象。

    Returns:
        消息文本内容。
    """
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(getattr(message, "content", message))


class JobAgent(BaseAgent):
    """岗位分析 Agent：根据用户求职意向查询真实岗位库并输出匹配分析。"""

    name: str = "job"
    description: str = "校招岗位分析与匹配推荐"

    _SYSTEM_PROMPT = """你是校招求职顾问。

## 可用工具
| 工具 | 调用时机 |
|------|---------|
| search_jobs | 用户询问岗位推荐、岗位分析时 |
| knowledge_search | 需要专业知识支撑时 |
| get_latest_ability | 推荐前读取用户能力画像 |
| save_memory | 发现用户稳定偏好时 |

## 工作流程
1. 推荐前先调 get_latest_ability 读能力画像：有数据按维度分数说明理由，无数据不给分数结论
2. 用 search_jobs 查询真实岗位（按用户意向构造关键词）
3. 结合岗位数据给出推荐与匹配分析
4. 发现稳定偏好时 save_memory

## 输出格式
- 推荐岗位表格：岗位名 | 公司 | 城市 | 薪资 | 匹配度
- 匹配分析：为什么适合
- 投递建议：下一步行动

## 安全边界
- 严禁编造岗位信息
- 无结果时建议放宽条件"""

    def __init__(self, settings: Settings) -> None:
        """初始化岗位分析 Agent 并注册工具。

        LLM 实例延迟创建（不在启动阶段依赖模型 Key）；旧工具内部持有
        服务账号鉴权客户端；ReAct 工具依赖（业务客户端 / 知识库 / 长期
        记忆）由基类延迟创建并复用。

        Args:
            settings: 全局配置。
        """
        super().__init__(settings)
        # 旧工具（同步，供 run/stream_run 使用）
        self.register_tool(LegacySearchJobsTool(BusinessServiceClient(settings)))

    # ==================== ReAct 钩子 ====================

    def _get_langchain_tools(self, state: AgentState) -> list:
        """返回岗位 Agent 的 LangChain 工具列表（按请求构建，注入 user_id）。

        Args:
            state: 当前图状态。

        Returns:
            [SearchJobsTool, KnowledgeSearchTool, GetLatestAbilityTool,
             SaveMemoryTool]。
        """
        return [
            SearchJobsTool(business_client=self._get_business_client()),
            KnowledgeSearchTool(knowledge_service=self._get_knowledge_service()),
            GetLatestAbilityTool(
                business_client=self._get_business_client(),
                user_id=self._user_id_to_int(state.get("user_id")),
            ),
            SaveMemoryTool(
                user_id=self._user_id_to_int(state.get("user_id")),
                long_term_memory=self._get_long_term_memory(),
            ),
        ]

    def _build_system_prompt(self) -> str:
        """构建 ReAct 系统提示词（精简版）。"""
        return self._SYSTEM_PROMPT

    def _get_llm(self) -> Any:
        """延迟创建并缓存本 Agent 的对话模型。

        Returns:
            langchain ChatOpenAI 实例（模型/密钥来自 job 专属配置）。
        """
        if self._llm is None:
            self._llm = get_llm_factory().create_chat_llm(self.name)
        return self._llm

    @staticmethod
    def _format_history(messages: Optional[List[Any]]) -> str:
        """将对话历史格式化为文本。

        Args:
            messages: 历史消息列表，元素为 dict 或 LangChain 消息。

        Returns:
            拼接后的多行历史文本；无历史返回空字符串。
        """
        if not messages:
            return ""
        recent = messages[-_HISTORY_LIMIT:]
        return "\n".join(
            f"{_message_role(m)}: {_message_content(m)}" for m in recent
        )

    def get_prompt(
        self,
        query: str,
        rag_context: Optional[str] = None,
        long_term_context: Optional[str] = None,
        history: Optional[List[Any]] = None,
        jobs_data: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """组装岗位分析提示词。

        Args:
            query: 用户求职意向。
            rag_context: 可选 RAG 参考资料（行业/岗位知识）。
            long_term_context: 可选用户长期记忆区块文本（无记忆为 None）。
            history: 可选对话历史。
            jobs_data: 工具查询得到的真实岗位列表文本。
            **kwargs: 预留扩展参数。

        Returns:
            完整提示词字符串。
        """
        # 用户内容隔离：系统提示词（含安全边界条款）恒位于 parts 首位，用户原文
        # 只出现在【用户意向】/【对话历史】等后置区块，防止用户输入注入改写
        # 系统指令（提示词注入的"位置防御"原则）。
        parts: List[str] = [self._SYSTEM_PROMPT]
        if rag_context:
            parts.append(f"【参考资料】\n{rag_context}")
        if long_term_context:
            parts.append(f"【用户长期记忆】\n{long_term_context}")
        history_text = self._format_history(history)
        if history_text:
            parts.append(f"【对话历史】\n{history_text}")
        if jobs_data:
            parts.append(f"【岗位数据】\n{jobs_data}")
        parts.append(f"【用户意向】\n{query}")
        return "\n\n".join(parts)

    def _build_prompt(self, state: AgentState) -> str:
        """从图状态组装岗位分析完整提示词（同步 / 流式共用）。

        顺序：先同步调用 ``search_jobs`` 工具查询真实在招岗位（快速调用，
        置于大模型生成之前），再构造【岗位数据】区块，最后连同 RAG 参考资料、
        对话历史与用户意向交由 :meth:`get_prompt` 组装。工具异常时降级为
        通用建议，不阻断后续生成。

        Args:
            state: 当前图状态，读取 user_input / messages / rag_context。

        Returns:
            完整提示词字符串。
        """
        query = state.get("user_input", "")

        # 工具调用：查询在招岗位（固定 status=1，由工具/客户端默认保证）
        try:
            jobs = self.call_tool(
                "search_jobs", page_num=1, page_size=_JOB_FETCH_SIZE
            )
            records = jobs.get("list", []) if isinstance(jobs, dict) else []
        except Exception as exc:  # noqa: BLE001 - 工具异常降级，不阻断主流程
            self._logger_debug(f"岗位查询失败，降级为通用建议: {exc}")
            records = []
            state["error"] = f"岗位查询失败: {exc}"

        if records:
            jobs_data = "\n".join(
                f"- {r.get('positionName', '')} | {r.get('companyName', '')} | "
                f"{r.get('workCity', '')} | {r.get('salaryNote', '')} | "
                f"学历:{r.get('educationText', '')} | "
                f"{str(r.get('jobDescription', ''))[:_JOB_DESC_LIMIT]}"
                for r in records
            )
        else:
            jobs_data = (
                "（当前无在招岗位数据或岗位库暂不可用，请仅基于用户意向给出"
                "通用的求职方向与能力准备建议，并说明未查询到实时岗位）"
            )

        return self.get_prompt(
            query,
            rag_context=state.get("rag_context"),
            history=state.get("messages"),
            jobs_data=jobs_data,
            long_term_context=self._resolve_long_term_context(state),
        )

    def run(self, state: AgentState) -> AgentState:
        """执行岗位分析（同步，图批处理路径）：组提示词 → 大模型生成。

        提示词组装（含工具查询）见 :meth:`_build_prompt`；大模型异常统一
        写入 ``state["error"]`` 并给出友好提示，不向上抛出。流式场景请使用
        继承自基类的 :meth:`stream_run`。

        Args:
            state: 当前图状态，读取 user_input / messages / rag_context。

        Returns:
            更新后的图状态（含 final_response / llm_response）。
        """
        prompt = self._build_prompt(state)

        try:
            resp = self._get_llm().invoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
        except Exception as exc:  # noqa: BLE001 - 统一捕获写入状态，不抛出
            state["error"] = str(exc)
            state["final_response"] = "岗位分析服务暂时不可用，请稍后再试"
            return state

        content = (content or "").strip()
        if not content:
            state["final_response"] = "暂时无法生成岗位分析，请换一种描述后再试"
            return state

        state["llm_response"] = content
        state["final_response"] = content
        return state
