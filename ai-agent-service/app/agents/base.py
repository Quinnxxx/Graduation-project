"""Agent 基类。

定义标准接口：

**旧接口（同步，单次 LLM 调用）**：
- :meth:`BaseAgent.run`：同步执行主逻辑，用于图批处理
- :meth:`BaseAgent.stream_run`：异步 token 级流式执行，用于流式对话
- :meth:`BaseAgent._build_prompt`：从图状态组装完整提示词
- :meth:`BaseAgent.get_prompt`：底层提示词组装函数
- :meth:`BaseAgent.call_tool`：调用工具，基于内部注册表分发

**新接口（异步，ReAct 循环）**：
- :meth:`BaseAgent.arun`：ReAct 版本，LLM 经 function calling 自主调用工具
- :meth:`BaseAgent.astream_run`：ReAct 流式版本，逐 token 输出
- :meth:`BaseAgent._get_langchain_tools`：返回 LangChain 协议工具列表
- :meth:`BaseAgent._build_system_prompt`：构建系统提示词

所有具体 Agent（岗位分析、简历优化、技术 / HR 面试等）继承本类，
通过 ``register_tool`` 插件化注册工具；同步 ``run`` 与异步 ``stream_run``
共享同一套 ``_build_prompt`` 提示词组装逻辑，保证批处理与流式输出一致。

ReAct 模式下，Agent 通过 :meth:`arun` 执行"推理→行动→观察"多轮循环，
LLM 自主决定调用哪个工具、是否继续、如何完成任务。
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from loguru import logger

from app.config.settings import Settings
from app.graph.state import AgentState
from app.tools.base import BaseTool
from app.utils.exceptions import ToolError


class BaseAgent(ABC):
    """Agent 抽象基类。

    Attributes:
        name: Agent 唯一名称。
        description: Agent 能力描述。
    """

    name: str = "base_agent"
    description: str = "Agent 能力描述"

    def __init__(self, settings: Settings, llm: Optional[Any] = None) -> None:
        """初始化 Agent。

        Args:
            settings: 全局配置。
            llm: 大模型实例（langchain ChatOpenAI 等），缺省为 None，
                由子类按需创建或延迟注入。
        """
        self._settings = settings
        self._llm = llm
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """注册工具到 Agent（插件化扩展入口）。

        Args:
            tool: 工具实例。
        """
        self._tools[tool.name] = tool
        self._logger_debug(f"工具已注册: {tool.name}")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """按名称获取已注册工具。

        Args:
            tool_name: 工具名称。

        Returns:
            工具实例，未注册返回 None。
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出全部已注册工具的元信息。

        Returns:
            工具元信息列表（供 LLM function calling / 提示词消费）。
        """
        return [tool.to_dict() for tool in self._tools.values()]

    @staticmethod
    def format_long_term_context(
        memories: Optional[List[Dict[str, Any]]],
    ) -> str:
        """将用户长期记忆条目渲染为提示词区块文本（各 Agent 复用）。

        每条记忆输出一行 "- {content}"；入口无记忆（None / 空列表）返回
        空字符串，由调用方决定是否拼接【用户长期记忆】区块。

        Args:
            memories: 长期记忆条目列表（load 返回 [{id, memory_type, content,
                importance, source, create_time}]），可为 None / 空。

        Returns:
            渲染后的条目文本；无记忆返回空字符串。
        """
        if not memories:
            return ""
        lines = []
        for memory in memories:
            content = str(memory.get("content", "")).strip() if isinstance(memory, dict) else str(memory).strip()
            if content:
                lines.append(f"- {content}")
        return "\n".join(lines)

    def _resolve_long_term_context(self, state: AgentState) -> Optional[str]:
        """从图状态解析【用户长期记忆】区块文本（各 Agent 复用）。

        兼容两种形态：``state["long_term_context"]`` 已是格式化文本（str）
        时直接复用；为 List（:meth:`LongTermMemory.load` 原始返回）时调用
        :meth:`format_long_term_context` 渲染；无记忆（缺失 / 空 / None）
        返回 None，由 get_prompt 决定不拼接区块。

        Args:
            state: 当前 AgentState，读取 long_term_context 字段。

        Returns:
            区块文本；无记忆返回 None。
        """
        raw = state.get("long_term_context")
        text = raw if isinstance(raw, str) else self.format_long_term_context(raw)
        return text or None

    @abstractmethod
    def get_prompt(self, query: str, **kwargs: Any) -> str:
        """构建 Agent 提示词。

        Args:
            query: 用户输入。
            **kwargs: 附加上下文（历史消息、检索结果、工具信息等）。

        Returns:
            最终提示词字符串。
        """

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        """执行 Agent 主逻辑（同步，用于 LangGraph 图批处理）。

        实现约定：
        1. 先通过 :meth:`_build_prompt` 组装完整提示词（含工具结果 / RAG /
           历史 / 简历等上下文）；
        2. 通过 :meth:`call_tool` 调用工具；
        3. 结果写入 state["final_response"]，异常写入 state["error"]，
           同步路径自行捕获大模型异常，不向上抛出。

        Args:
            state: 当前 AgentState。

        Returns:
            更新后的 AgentState。
        """

    def _build_prompt(self, state: AgentState) -> str:
        """从图状态组装完整提示词（同步 / 流式共用）。

        职责：读取 state 中的 user_input / messages / rag_context /
        resume_text 等字段，必要时先调用工具，再拼装系统提示词与各上下文
        区块，返回最终送入大模型的提示词字符串。

        Args:
            state: 当前 AgentState。

        Returns:
            完整提示词字符串。

        Raises:
            NotImplementedError: 子类未实现本方法时。
        """
        raise NotImplementedError("Agent must implement _build_prompt")

    async def stream_run(self, state: AgentState) -> AsyncIterator[str]:
        """异步 token 级流式执行（默认实现，子类无需覆写）。

        流程：先通过 :meth:`_build_prompt` 组装提示词，再调用大模型的
        ``astream`` 接口逐块产出文本，跳过空块，结束后将完整内容回写
        ``state["llm_response"]`` 与 ``state["final_response"]``。

        与同步 :meth:`run` 不同，本方法**不捕获异常**：token 级流式生成
        过程中的任何异常都向上抛出，由编排层（图构建器 ``run_stream``）
        统一兜底并向客户端下发 error 事件，避免在生成中途返回不一致状态。

        Args:
            state: 当前 AgentState（同时承载组装所需输入与最终结果）。

        Yields:
            每个增量文本块（str）。
        """
        prompt = self._build_prompt(state)
        llm = self._get_llm()
        content = ""
        async for chunk in llm.astream(prompt):
            text = chunk.content if hasattr(chunk, "content") else str(chunk)
            if not text:
                # 跳过空块（部分模型会产出仅含 usage / role_meta 的块）
                continue
            content += text
            yield text
        state["llm_response"] = content
        state["final_response"] = content

    def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """调用已注册工具，异常统一包装为 :class:`ToolError`。

        Args:
            tool_name: 工具名称。
            **kwargs: 工具入参。

        Returns:
            工具执行结果。

        Raises:
            ToolError: 工具不存在或执行失败时。
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolError(f"工具不存在: {tool_name}")
        try:
            result = tool.run(**kwargs)
            self._logger_debug(f"工具调用成功: {tool_name}")
            return result
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(
                f"工具 {tool_name} 执行失败: {exc}", cause=exc
            ) from exc

    def _logger_debug(self, message: str) -> None:
        """子类可覆写的日志钩子，避免基类强依赖 loguru 导入。

        Args:
            message: 日志消息。
        """
        from loguru import logger  # 延迟导入，避免基类硬依赖

        logger.debug(f"[{self.name}] {message}")

    # ==================== ReAct 执行方法 ====================

    def _get_langchain_tools(self, state: AgentState) -> list:
        """返回 LangChain 协议工具列表（子类重写）。

        工具可能注入 ``state["user_id"]``（如画像 / 简历 / 能力 / 记忆写入），
        因此一律**按请求**构建、不做跨请求缓存，避免用户数据串号。

        Args:
            state: 当前图状态（读取 user_id 等）。

        Returns:
            LangChain BaseTool 实例列表，供 ReAct 子图消费。
            默认返回空列表，子类应重写以返回实际工具。
        """
        return []

    def _build_system_prompt(self) -> str:
        """构建系统提示词（子类重写）。

        Returns:
            系统提示词字符串，用于 ReAct 子图的 state_modifier。
            子类必须重写以返回实际提示词。

        Raises:
            NotImplementedError: 子类未实现本方法时。
        """
        raise NotImplementedError("Agent must implement _build_system_prompt")

    def _build_input_messages(self, state: AgentState) -> list:
        """构建输入消息列表（子类可重写）。

        默认实现：注入对话历史 + 用户当前输入。

        Args:
            state: 当前图状态。

        Returns:
            LangChain 消息列表。
        """
        messages = []
        # 注入对话历史（兼容 dict 和 LangChain 消息）
        for msg in state.get("messages", []):
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
            else:
                # 已是 LangChain 消息对象，直接使用
                messages.append(msg)
        # 注入用户当前输入
        user_input = state.get("user_input", "")
        if user_input:
            messages.append(HumanMessage(content=user_input))
        return messages

    def _build_react_graph(self, tools: list) -> Any:
        """构建 ReAct 子图。

        工具注入用户上下文（user_id），同一 Agent 每次请求的工具实例都不同，
        因此**不缓存**图，按次构建保证用户数据不串号；create_react_agent 图
        构建开销为微秒级，不影响单条消息的生成体验。

        Args:
            tools: LangChain 工具列表。

        Returns:
            编译后的 ReAct 子图（CompiledStateGraph）。
        """
        system_prompt = self._build_system_prompt()
        graph = create_react_agent(
            model=self._get_llm(),
            tools=tools,
            state_modifier=system_prompt,
        )
        logger.debug(
            "[{}] ReAct 子图构建完成: tools={}",
            self.name,
            [t.name for t in tools],
        )
        return graph

    # ==================== 工具依赖注入（子类复用） ====================

    def _get_business_client(self) -> Any:
        """延迟创建并缓存 business-service 客户端（进程内复用）。

        Returns:
            BusinessServiceClient 实例。
        """
        if not hasattr(self, "_dep_business_client"):
            from app.services.business_client import BusinessServiceClient

            self._dep_business_client = BusinessServiceClient(self._settings)
        return self._dep_business_client

    def _get_knowledge_service(self) -> Any:
        """延迟创建并缓存知识库服务（进程内复用）。

        KnowledgeService 构造需要 MilvusClient；Milvus 客户端为懒连接
        无状态封装（行为与 main 生命周期注入的实例一致），此处独立创建，
        保证 Agent 自包含、不依赖启动时序。

        Returns:
            KnowledgeService 实例。
        """
        if not hasattr(self, "_dep_knowledge_service"):
            from app.rag.base import MilvusClient
            from app.rag.knowledge_service import KnowledgeService

            self._dep_knowledge_service = KnowledgeService(
                self._settings, MilvusClient(self._settings)
            )
        return self._dep_knowledge_service

    def _get_long_term_memory(self) -> Any:
        """延迟创建并缓存长期记忆模块（进程内复用）。

        Returns:
            LongTermMemory 实例。
        """
        if not hasattr(self, "_dep_long_term_memory"):
            from app.memory.long_term import LongTermMemory

            self._dep_long_term_memory = LongTermMemory(self._settings)
        return self._dep_long_term_memory

    @staticmethod
    def _user_id_to_int(user_id: Any) -> int:
        """将 state 中的 user_id 安全转为 int（工具注入用）。

        Args:
            user_id: 图状态中的 user_id（str / int）。

        Returns:
            整数 user_id，非法输入回退为 0（表示匿名）。
        """
        try:
            return int(user_id)
        except (TypeError, ValueError):
            return 0

    async def arun(self, state: AgentState) -> str:
        """ReAct 版本：LLM 自主决定调用工具。

        执行流程：
        1. 获取 LangChain 工具列表
        2. 构建 ReAct 子图
        3. 构建输入消息
        4. 执行 ReAct 循环（ainvoke）
        5. 提取最终回复

        Args:
            state: 当前图状态。

        Returns:
            最终回复文本。
        """
        tools = self._get_langchain_tools(state)
        if not tools:
            logger.warning("[{}] 无 LangChain 工具，ReAct 退化为单次调用", self.name)
            # 降级为单次调用
            prompt = self._build_prompt(state)
            resp = self._get_llm().invoke(prompt)
            return resp.content if hasattr(resp, "content") else str(resp)

        graph = self._build_react_graph(tools)
        messages = self._build_input_messages(state)

        try:
            result = await graph.ainvoke({"messages": messages})
            # 提取最终回复（最后一条 AIMessage 的 content）
            final_message = result["messages"][-1]
            if isinstance(final_message, AIMessage):
                return final_message.content or ""
            return str(final_message)
        except Exception as exc:
            logger.exception("[{}] ReAct 执行失败", self.name)
            return f"AI 服务执行失败: {exc}"

    async def astream_run(self, state: AgentState) -> AsyncIterator[str]:
        """ReAct 流式版本：输出最终回复的文本增量。

        **langgraph 0.1.10 实测限制**：create_react_agent 的模型节点使用
        非流式 ``invoke``，``stream_mode="messages"`` 不产出任何事件；改用
        默认 ``updates`` 流式，每轮更新携带整条 AI 消息。因此本方法的
        "流式"粒度为 **逐轮 AI 消息**（工具调用轮的消息不带最终文本会被
        过滤），而非逐 token。若需 token 级输出，需升级 langgraph 或
        自实现 ReAct 循环（见交付报告遗留限制）。

        执行流程：
        1. 获取 LangChain 工具列表（注入 user_id）
        2. 构建 ReAct 子图
        3. 构建输入消息
        4. ``astream`` 遍历 updates：yield 无工具调用的 AI 消息文本
        （即最终回复；工具调用轮的带 thinking 文本会一并被过滤）

        Args:
            state: 当前图状态。

        Yields:
            AI 回复文本块（整段级，工具调用轮不产出）。
        """
        tools = self._get_langchain_tools(state)
        if not tools:
            logger.warning("[{}] 无 LangChain 工具，ReAct 流式退化为单次调用", self.name)
            # 降级为单次流式调用
            prompt = self._build_prompt(state)
            async for chunk in self._get_llm().astream(prompt):
                text = chunk.content if hasattr(chunk, "content") else str(chunk)
                if text:
                    yield text
            return

        graph = self._build_react_graph(tools)
        messages = self._build_input_messages(state)

        try:
            async for event in graph.astream({"messages": messages}):
                # updates 模式事件为 {node_name: {state 更新}}
                if not isinstance(event, dict):
                    continue
                for node_name, update in event.items():
                    msgs = (
                        update.get("messages", [])
                        if isinstance(update, dict)
                        else []
                    )
                    for msg in msgs:
                        # 只保留最终回复：AI 消息、非空文本、且无工具调用
                        # （带 tool_calls 的 AI 消息可能是思考文本，非最终答复）
                        if (
                            isinstance(msg, AIMessage)
                            and msg.content
                            and not getattr(msg, "tool_calls", None)
                        ):
                            yield msg.content
        except Exception as exc:
            logger.exception("[{}] ReAct 流式执行失败", self.name)
            yield f"AI 服务执行失败: {exc}"
