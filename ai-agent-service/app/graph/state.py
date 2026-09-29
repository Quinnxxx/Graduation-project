"""LangGraph 基础状态定义。

定义 Agent 图在节点间共享的 :class:`AgentState`，包含用户输入、对话历史、
中间结果、工具调用结果与用户标识。所有具体 Agent 图均基于该状态扩展。
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """Agent 图执行过程中的共享状态。

    Attributes:
        user_id: 当前用户唯一标识。
        user_input: 用户本轮原始输入。
        messages: 对话历史消息列表（LangGraph 消息 reducer 合并）。
        intermediate_results: 节点产出的中间结果（键值结构，供下游节点消费）。
        tool_call_results: 工具调用记录列表，元素为 {"tool": 工具名, "result": 结果}。
        final_response: 最终回复内容。
        error: 执行过程中记录的异常信息，None 表示无异常。
        intent: 意图路由结果：job/resume/tech/hr/chat。
        agent_name: 实际执行 Agent 的名称。
        rag_context: RAG 检索上下文，未检索为 None。
        llm_response: 大模型原始响应内容。
        stream_events: 预留流式事件通道（供流式响应扩展使用）。
        resume_text: 前端透传的用户简历文本（简历优化/面试场景使用）；
            由调用方在前端转发链路中透传，AI 服务不主动拉取用户私有数据。
        session_id: 业务侧会话/面试记录 ID（面试场景为 interview_record.id），
            用于 Redis 记忆失效后从持久化历史重建短期记忆；其他场景为空。
        long_term_context: 用户长期记忆条目（跨会话沉淀），供 Agent 提示词
            注入【用户长期记忆】区块；无记忆为空列表。
    """

    user_id: str
    user_input: str
    messages: Annotated[List[Any], add_messages]
    intermediate_results: Dict[str, Any]
    tool_call_results: List[Dict[str, Any]]
    final_response: str
    error: Optional[str]
    # ---- 图编排扩展字段（全部可选，不影响初始状态构建） ----
    intent: Optional[str]  # 意图路由结果：job/resume/tech/hr/chat
    agent_name: Optional[str]  # 实际执行Agent名
    rag_context: Optional[str]  # RAG检索上下文，未检索为None
    llm_response: Optional[str]  # 大模型原始响应
    stream_events: Optional[Any]  # 预留流式事件通道
    resume_text: Optional[str]  # 前端透传的用户简历文本（简历优化/面试场景使用）
    session_id: Optional[str]  # 业务侧会话/面试记录 ID（面试场景为 interview_record.id），
                               # 用于 Redis 记忆失效后从持久化历史重建短期记忆；其他场景为空
    long_term_context: List[Dict[str, Any]]  # 用户长期记忆条目（跨会话沉淀），无记忆为空列表


def create_initial_state(user_id: str, user_input: str) -> AgentState:
    """构建图执行的初始状态。

    Args:
        user_id: 用户唯一标识。
        user_input: 用户本轮输入。

    Returns:
        携带默认空值的初始 AgentState。
    """
    return {
        "user_id": user_id,
        "user_input": user_input,
        "messages": [],
        "intermediate_results": {},
        "tool_call_results": [],
        "final_response": "",
        "error": None,
    }
