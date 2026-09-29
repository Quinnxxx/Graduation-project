"""LangGraph 图构建器。

编排意图路由与各真实 Agent 节点，整体图结构：

``router → {job / resume / tech / hr / chat} → END``

- ``router``：两级路由节点（零成本、稳定，后续可替换为 LLM 意图识别），
  先按关键词显式识别意图，未命中时结合短期记忆延续用户当前会话 Agent；
- ``job_agent / resume_agent / tech_agent / hr_agent``：真实 Agent 节点，
  节点层统一完成「短期记忆注入 → RAG 上下文注入 → Agent 执行 → 记忆回写
  （含当前会话 Agent 标记）」，记忆与检索和 Agent 内部生成逻辑解耦；
- ``chat_agent``：自由问答兜底节点，直接调用默认模型。

本模块提供两条执行路径，共享同一套路由 / 记忆 / RAG / Agent 组件：

- :meth:`AgentGraphBuilder.build` 编译 LangGraph 图，以 ``ainvoke``
  批处理方式一次性返回完整结果（适合离线 / 非流式调用）；
- :meth:`AgentGraphBuilder.run_stream` 为异步生成器，承载 token 级流式
  输出（meta / chunk / final / error 事件），避免图框架在流式场景的额外
  开销，适合 SSE / WebSocket 等实时对话。

本模块只负责图结构、路由与上下文装配，不承载具体生成逻辑。
"""

import asyncio
import json
import re
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Tuple

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from app.agents.registry import AgentRegistry
from app.config.settings import Settings
from app.graph.state import AgentState
from app.llm.factory import LLMFactory, get_llm_factory
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory
from app.rag.knowledge_service import KnowledgeService
from app.utils.exceptions import ConfigError


class AgentGraphBuilder:
    """Agent 图构建器。

    依据意图路由表构建一张固定的状态图：入口 router 节点按用户输入
    规则匹配意图，将执行流转到对应 Agent 节点；Agent 节点在执行前后
    统一注入 / 回写短期记忆，并按场景注入 RAG 知识上下文，各节点结束后
    写入 ``final_response`` 并终止。

    Attributes:
        _settings: 全局配置。
        _registry: Agent 注册表。
        _llm_factory: LLM 客户端工厂（供 chat 兜底节点使用）。
        _short_term_memory: 短期记忆实例，None 时节点跳过记忆读写。
        _knowledge_service: 知识库服务，None 时节点跳过 RAG 检索。
    """

    # Agent 场景 → RAG 文档类型映射（doc_type：1面经 2简历模板 3面试技巧
    # 4行业知识 5岗位知识；None 表示不限类型）
    _AGENT_RAG_DOC_TYPES: Dict[str, Optional[int]] = {
        "job": None,
        "resume": 2,
        "tech": 1,
        "hr": 3,
    }

    # 显式换场景意图表：会话延续期（active_agent 存活）内，仅当输入命中
    # 本表的"动作型强短语"才允许切换场景；列表有序、首个命中即返回。
    # 刻意去掉"岗位/招聘/简历/技术"等宽泛单字兜底，避免面试回答中
    # 偶现的场景词（如"做过一个校园招聘平台项目"里的"招聘"）被误路由。
    # chat 词条置于最末：命中即视为场景终结（清除 active_agent 标记），
    # 使复盘报告 / 自由问答等一次性任务不被旧场景延续劫持。
    _SWITCH_INTENTS: List[Tuple[str, List[str]]] = [
        ("resume", ["优化简历", "简历优化", "改简历", "写简历", "投简历", "帮我改"]),
        ("tech", ["技术面试", "技术面", "开始面试", "模拟面试"]),
        ("hr", ["hr面试", "hr面", "行为面", "面试一下"]),
        (
            "job",
            [
                "岗位匹配",
                "匹配岗位",
                "岗位推荐",
                "推荐岗位",
                "职位推荐",
                "推荐职位",
                "找工作",
                "找岗位",
                "校招信息",
                "校招岗位",
                "招聘信息",
            ],
        ),
        ("chat", ["复盘报告", "面试复盘", "能力复盘", "自由问答"]),
    ]

    def __init__(
        self,
        settings: Settings,
        registry: AgentRegistry,
        short_term_memory: Optional[ShortTermMemory] = None,
        knowledge_service: Optional[KnowledgeService] = None,
        long_term_memory: Optional[LongTermMemory] = None,
    ) -> None:
        """初始化构建器。

        Args:
            settings: 全局配置。
            registry: Agent 注册表。
            short_term_memory: 短期记忆实例（可为 None，节点跳过记忆读写）。
            knowledge_service: 知识库服务（可为 None，节点跳过 RAG 检索）。
            long_term_memory: 长期记忆实例（可为 None，节点跳过长期记忆读取）。
        """
        self._settings = settings
        self._registry = registry
        self._llm_factory = LLMFactory(settings)
        self._short_term_memory = short_term_memory
        self._knowledge_service = knowledge_service
        self._long_term_memory = long_term_memory
        # 复盘沉淀幂等键：进程内 (user_id, query) 去重，防止同一复盘请求
        # 重复点击触发重复沉淀（LLM 报告每次内容可能不同，MySQL 无法精确去重）
        self._distilled_keys: Set[Tuple[str, str]] = set()

    async def _router_node(self, state: AgentState) -> dict:
        """规则路由节点（不调用 LLM）。

        两级路由语义：
        1. 会话延续优先（active_agent 存活期内）：仅当输入命中
           :attr:`_SWITCH_INTENTS` 中的"动作型强短语"才视为显式换场景并
           允许切换；否则一律延续当前场景——即使回答内容包含其他场景的
           宽泛词（如技术面试中"做过一个校园招聘平台项目"里的"招聘"）也
           不被误路由。chat 强短语命中即视为场景终结：清除 active_agent
           标记（失败仅日志告警），使复盘报告 / 自由问答等一次性任务结束
           后不再被旧场景延续劫持。
        2. 无会话上下文（首次进入 / 标记过期 / 无记忆实例）：走全量
           关键词表 :data:`intent_rules` 做首次意图识别，未命中回落 chat。

        后续可整体替换为 LLM 意图识别（保留扩展点）。

        Args:
            state: 当前 AgentState。

        Returns:
            意图路由结果 {"intent": job/resume/tech/hr/chat}。
        """
        query = state.get("user_input", "") or ""
        query_lower = query.lower()
        user_id = state.get("user_id", "")

        # 第一级：存在会话上下文时，仅"显式换场景短语"允许切换，否则延续
        if self._short_term_memory is not None and user_id:
            active_agent = await self._short_term_memory.get_active_agent(user_id)
            # 场景标记缺失（如跨天 / 重启后）：若为面试场景（state 带 session_id），
            # 先从 MySQL 持久化问答重建短期记忆并恢复场景标记，再判断延续。
            if active_agent not in self._AGENT_RAG_DOC_TYPES:
                rebuilt_agent = await self._warm_rebuild_if_needed(state, user_id)
                if rebuilt_agent in ("tech", "hr"):
                    active_agent = rebuilt_agent
            if active_agent in self._AGENT_RAG_DOC_TYPES:
                for intent, keywords in self._SWITCH_INTENTS:
                    for keyword in keywords:
                        if keyword.lower() in query_lower:
                            logger.debug(
                                "会话延续期内显式换场景: user_id={}, agent={} -> {}",
                                user_id,
                                active_agent,
                                intent,
                            )
                            # chat 强短语命中即场景终结：清除延续标记，
                            # 清除后下一条请求走 chat 兜底，不再被旧场景劫持
                            if intent == "chat":
                                try:
                                    await self._short_term_memory.clear_active_agent(
                                        user_id
                                    )
                                except Exception as exc:  # noqa: BLE001 - 清除失败仅告警
                                    logger.warning(
                                        "当前会话 Agent 清除失败: user_id={}, err={}",
                                        user_id,
                                        exc,
                                    )
                            return {"intent": intent}
                logger.debug(
                    "会话延续期内无切换意图，延续 Agent: user_id={}, agent={}",
                    user_id,
                    active_agent,
                )
                return {"intent": active_agent}

        # 第二级：无会话上下文时，按关键词表顺序做首次意图识别（顺序即优先级）
        # resume 置于首位，凡提及"简历"优先按简历优化处理；
        # 面试类（tech/hr）先于 job，避免"目标岗位"等面试语料被岗位意图抢先；
        # "岗位/招聘/投递"等兜底覆盖"推荐…岗位""优化这份简历"等自然说法。
        intent_rules: List[Tuple[str, List[str]]] = [
            ("resume", ["简历", "简历优化", "优化简历", "改简历", "resume"]),
            ("tech", ["技术面试", "技术面", "八股", "算法题", "手撕"]),
            ("hr", ["hr面试", "hr面", "行为面", "hr"]),
            ("job", ["岗位匹配", "匹配岗位", "岗位推荐", "推荐岗位", "职位推荐", "找工作", "找岗位", "校招", "职位", "岗位", "招聘", "投递", "内推", "jd", "job"]),
        ]
        for intent, keywords in intent_rules:
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    return {"intent": intent}

        # 既无显式意图也无会话上下文：兜底为自由问答
        return {"intent": "chat"}

    async def _warm_rebuild_if_needed(
        self, state: AgentState, user_id: str
    ) -> Optional[str]:
        """Redis 短期记忆失效后，从持久化面试问答重建短期记忆（记忆热启动）。

        触发条件（全部满足）：
        1. state 携带 ``session_id``（面试场景，值为 interview_record.id）；
        2. Redis 短期记忆当前为空（非空说明记忆仍在，不重复重建，保证幂等）。

        安全：拉取时显式传 user_id，business 服务层校验面试归属，
        防止前端把 session_id 篡改为他人面试。

        Args:
            state: 当前图状态（取 session_id）。
            user_id: 当前用户 ID（字符串）。

        Returns:
            重建成功返回场景名（"tech"/"hr"）；无需重建 / 无历史 / 失败返回 None。
        """
        session_id = state.get("session_id")
        if not session_id:
            return None
        try:
            uid_int = int(user_id)
            interview_id = int(session_id)
        except (TypeError, ValueError):
            return None

        # 短期记忆非空则不重建（幂等：重建过或记忆仍在都不重复写入）
        if self._short_term_memory is not None:
            try:
                existing = await self._short_term_memory.get_messages(
                    user_id, limit=1
                )
                if existing:
                    return None
            except Exception as exc:  # noqa: BLE001 - 读取失败不阻断，继续尝试重建
                logger.warning("重建前短期记忆检查失败: {}", exc)

        # 拉取持久化面试详情（内部令牌通道；归属不符会抛 ExternalServiceError）。
        # business_client 为同步 httpx 实现，放线程池执行，避免阻塞事件循环。
        try:
            if not hasattr(self, "_warm_business_client"):
                from app.services.business_client import BusinessServiceClient

                self._warm_business_client = BusinessServiceClient(self._settings)
            detail = await asyncio.to_thread(
                self._warm_business_client.get_interview_detail,
                uid_int,
                interview_id,
            )
        except Exception as exc:  # noqa: BLE001 - 拉取失败不阻断路由，回落正常逻辑
            logger.warning("面试持久化历史拉取失败: {}", exc)
            return None
        if not detail:
            return None

        messages = detail.get("messages") or []
        # 启动指令（历史数据可能把"开始面试"误落为 user answer）重建时过滤
        skip_user_phrases = {
            "开始面试", "开始技术面试", "开始hr面试", "模拟面试",
        }
        rebuilt = 0
        for msg in messages:
            role = msg.get("role")
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            if role == "user":
                if content.lower() in skip_user_phrases:
                    continue
                await self._short_term_memory.add_message(
                    user_id, "user", content
                )
                rebuilt += 1
            elif role == "assistant":
                await self._short_term_memory.add_message(
                    user_id, "assistant", content
                )
                rebuilt += 1

        if rebuilt == 0:
            return None

        # interviewType：1 技术 → tech；2 HR → hr
        agent_name = "hr" if detail.get("interviewType") == 2 else "tech"
        await self._short_term_memory.set_active_agent(user_id, agent_name)
        logger.info(
            "面试短期记忆已从持久化历史重建: user_id={}, interview_id={}, "
            "messages={}, agent={}",
            user_id,
            interview_id,
            rebuilt,
            agent_name,
        )
        return agent_name

    def _build_rag_context(self, agent_name: str, query: str) -> str:
        """按 Agent 场景检索知识库并格式化 RAG 上下文。

        知识库不可用、检索失败或无结果时返回空字符串，不阻断 Agent 执行；
        检索采用两阶段（向量召回 + Rerank 精排），失败由服务内部降级。

        Args:
            agent_name: Agent 名称（job/resume/tech/hr）。
            query: 用户输入，作为检索 query。

        Returns:
            格式化后的知识参考文本；无内容时返回空字符串。
        """
        if self._knowledge_service is None:
            return ""
        doc_type = self._AGENT_RAG_DOC_TYPES.get(agent_name)
        try:
            items = self._knowledge_service.search(
                query, top_k=3, doc_type=doc_type
            )
        except Exception as exc:  # noqa: BLE001 - RAG 失败降级，不阻断主流程
            logger.warning("RAG 检索失败: {}", exc)
            return ""
        if not items:
            return ""
        lines = ["【知识参考】"]
        for item in items:
            title = item.get("doc_title", "")
            content = str(item.get("content", ""))[:200]
            lines.append(f"- (来源: {title}) {content}")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_user_input(text: str) -> str:
        """清洗用户输入（提示词注入防护第一道防线）。

        规则：剔除控制字符与零宽/方向标记等格式化字符（保留中文/字母/数字/
        常见标点）；连续 3 行以上空行折叠为 2 行、行内连续空白折叠为单空格；
        超长输入截断至 2000 字符并追加截断提示；清洗异常（极端输入）回退为
        空字符串，不阻断主流程。

        Args:
            text: 原始用户输入。

        Returns:
            清洗后的文本（恒非 None，可能为空串）。
        """
        try:
            raw = str(text or "")
            # 控制字符 + 零宽/方向标记等不可见格式化字符
            cleaned = re.sub(
                r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028\u2029\ufeff]", "", raw
            )
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # 空行折叠
            cleaned = re.sub(r"[ \t\xa0]+", " ", cleaned)  # 行内空白折叠
            cleaned = cleaned.strip()
            if len(cleaned) > 2000:
                cleaned = cleaned[:2000] + "\n[输入过长，已截断]"
            return cleaned
        except Exception:  # noqa: BLE001 - 极端输入清洗失败回退空串
            logger.warning("用户输入清洗失败，回退为空")
            return ""

    def _is_review_query(self, query: str) -> bool:
        """判定是否复盘请求：query 命中 _SWITCH_INTENTS 中 chat 强短语之一。

        与路由复用同一张强短语表，保证"判定"与"路由到 chat（复盘）"语义一致。

        Args:
            query: 用户一次对话输入。

        Returns:
            True 表示应触发复盘沉淀。
        """
        query_lower = (query or "").lower()
        for intent, keywords in self._SWITCH_INTENTS:
            if intent != "chat":
                continue
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    return True
        return False

    def _memory_type_for(self, text: str) -> int:
        """按内容启发式分配记忆类型：能力画像=1/项目经历=2/技能偏好=3/面试教训=4。

        Args:
            text: 复盘报告小节文本。

        Returns:
            分配的 memory_type。优先级：技能偏好 > 项目经历 > 面试教训 > 能力画像。
        """
        t = (text or "").lower()
        if any(k in t for k in ("技能", "技术栈", "掌握", "熟悉", "框架", "spring", "redis")):
            return 3
        if any(k in t for k in ("项目", "亮点", "经历", "成果", "实现", "负责")):
            return 2
        if any(k in t for k in ("建议", "待改进", "改进", "不足", "教训", "提升", "加强")):
            return 4
        return 1

    def _extract_review_sections(self, response: str) -> List[Tuple[str, int]]:
        """从复盘 Markdown 文本抽取要点段落（第一期为精简版本）。

        按 Markdown 标题（``#``~``######``）切段，取非空前 4 段，每段作为一条
        记忆（单段截断 500 字符防超 Milvus content 上限）；无有效标题段时降级
        为整篇截断 2000 字符作为单条 memory_type=4 的沉淀。

        Args:
            response: 复盘报告完整 Markdown 文本。

        Returns:
            要点列表 [(content, memory_type), ...]，恒非空（至少含降级单条）。
        """
        parts = [p.strip() for p in re.split(r"\n(?=#{1,6}\s)", response)]
        sections: List[Tuple[str, int]] = []
        for part in parts:
            if not part:
                continue
            content = part[:500]
            if len(content) < 20:  # 过滤标题残片 / 短噪声行
                continue
            sections.append((content, self._memory_type_for(part)))
            if len(sections) >= 4:
                break
        if not sections:
            sections = [(response[:2000], 4)]
        return sections

    # 事实抽取提示词：要求 LLM 输出（type, content）原子事实句 JSON 数组
    # 注意：示例 JSON 大括号需双写转义（提示词经 str.format 渲染，{response} 为占位符）
    _FACT_EXTRACT_PROMPT = (
        "请从以下面试复盘报告中抽取长期记忆事实条目，每条一根子句（≤60字），"
        "聚焦：1)用户能力画像 2)项目经历与亮点 3)技能&技术栈偏好 "
        "4)面试教训/待改进。输出 JSON 数组，每项{{\"type\":1|2|3|4,\"content\":\"事实句\"}}。"
        "只输出 JSON：\n{response}"
    )

    async def _extract_facts_with_llm(
        self, response: str
    ) -> Optional[List[Dict[str, Any]]]:
        """LLM 原子化事实抽取：从复盘报告抽取 (type, content) 事实句列表。

        用 default 模型按结构化提示词抽取，JSON 输出容错解析（优先 ```json
        块，其次首个 [...] 数组）；解析失败 / 输出为空 / 调用异常时返回 None，
        由调用方降级为章节切片——大模型可用性不影响复盘主链路的基本不变。

        Args:
            response: 复盘报告完整文本。

        Returns:
            去重后的事实列表 [{type, content}]（content≤100 字）；失败返回 None。
        """
        try:
            llm = get_llm_factory().create_chat_llm("default")
            prompt = self._FACT_EXTRACT_PROMPT.format(response=response)
            # 同步 invoke 移入线程池，避免阻塞事件循环（复盘沉淀在后台任务执行）
            raw = await asyncio.to_thread(llm.invoke, prompt)
            text = str(getattr(raw, "content", raw) or "").strip()
            facts = self._parse_fact_json(text)
        except Exception as exc:  # noqa: BLE001 - LLM 抽取失败降级切片
            logger.warning("LLM 事实抽取失败，降级章节切片: {}", exc)
            return None
        if not facts:
            logger.warning("LLM 事实抽取为空，降级章节切片")
            return None
        logger.info("LLM 事实抽取: count={}", len(facts))
        return facts

    @staticmethod
    def _parse_fact_json(raw: str) -> List[Dict[str, Any]]:
        """容错解析 LLM 输出的 JSON 数组并做类型校验 / 去重。

        Args:
            raw: LLM 原始输出文本。

        Returns:
            清洗后的事实列表 [{type, content}]；解析失败返回 []。
        """
        text = (raw or "").strip()
        if not text:
            return []
        block = re.search(r"```json\s*(.*?)\s*```", text, re.S)
        if block:
            text = block.group(1).strip()
        elif not text.startswith("["):
            # 提取首个 '[' 开始、到其对应 ']' 结束的 JSON 数组（区分字符串内括号）
            start = text.find("[")
            if start >= 0:
                depth = 0
                in_str = False
                escape = False
                end = -1
                for i in range(start, len(text)):
                    ch = text[i]
                    if in_str:
                        if escape:
                            escape = False
                        elif ch == "\\":
                            escape = True
                        elif ch == '"':
                            in_str = False
                    elif ch == '"':
                        in_str = True
                    elif ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                if end > start:
                    text = text[start : end + 1]
        try:
            items = json.loads(text)
        except Exception:  # noqa: BLE001 - 非法 JSON 由调用方降级切片
            return []
        if not isinstance(items, list):
            return []
        facts: List[Dict[str, Any]] = []
        seen: Set[Tuple[int, str]] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                memory_type = int(item.get("type"))
            except (TypeError, ValueError):
                continue
            content = str(item.get("content", "") or "").strip()
            if memory_type not in (1, 2, 3, 4) or not content:
                continue
            content = content[:100]
            key = (memory_type, content)
            if key in seen:
                continue
            seen.add(key)
            facts.append({"type": memory_type, "content": content})
        return facts

    async def distill_review(
        self, user_id: str, query: str, response: str
    ) -> Optional[int]:
        """面试复盘后置沉淀：LLM 原子化事实抽取后写入长期记忆。

        判定为复盘请求（query 命中 chat 强短语）且响应非空时，优先用
        :meth:`_extract_facts_with_llm` 抽取 (memory_type=1/2/3/4, content)
        原子事实句，逐条经 :meth:`LongTermMemory.save` 双写（importance=3，
        source="面试复盘"）；LLM 抽取失败 / 为空时降级为章节切片。幂等：
        进程内 (user_id, query) 键去重，同一 request 仅沉淀一次。任何失败
        仅 logger.warning，不抛出——沉淀是增强能力，不阻断复盘主链路。

        Args:
            user_id: 业务用户 ID。
            query: 触发沉淀的复盘 query（含"复盘报告"等 chat 强短语）。
            response: 复盘报告完整文本。

        Returns:
            本次写入记忆条数；判定非复盘 / 响应为空 / 幂等命中 / 无长期记忆
            实例时返回 None。
        """
        if not self._is_review_query(query):
            return None
        text = str(response or "").strip()
        if not text:
            return None
        if self._long_term_memory is None:
            return None
        key = (str(user_id), str(query))
        if key in self._distilled_keys:
            logger.debug("复盘沉淀幂等命中，跳过: user_id={}", user_id)
            return None
        self._distilled_keys.add(key)

        # LLM 原子化事实抽取（默认路径），失败 / 为空降级章节切片
        facts = await self._extract_facts_with_llm(text)
        sections = self._extract_review_sections(text)
        if facts:
            items = [(f["content"], int(f["type"])) for f in facts]
            llm_count = len(facts)
        else:
            items = [(content, memory_type) for content, memory_type in sections]
            llm_count = 0

        count = 0
        for content, memory_type in items:
            try:
                await self._long_term_memory.save(
                    user_id,
                    content,
                    memory_type=memory_type,
                    importance=3,  # 复盘沉淀价值高，默认 3
                    source="面试复盘",
                )
                count += 1
            except Exception as exc:  # noqa: BLE001 - 单条失败不中断整体沉淀
                logger.warning("复盘沉淀写入失败: {}", exc)
        if count:
            logger.info(
                "面试复盘沉淀完成: user_id={}, count={}, llm_facts={}, sections={}",
                user_id,
                count,
                llm_count,
                len(sections),
            )
        return count or None

    async def distill_dialogue(
        self, user_id: str, intent: str, query: str, response: str
    ) -> Optional[int]:
        """流式对话沉淀：真实 Agent 场景的高价值长响应写入长期记忆。

        立项范围（收紧为两类之一）：仅处理 intent ∈ job/resume/tech/hr 且
        final 文本长度 >200 字符的响应——
        - tech/hr 视为"模拟面试"沉淀（source="模拟面试"，importance=3）；
        - job/resume 视为"咨询对话"沉淀（source="咨询对话"，importance=2）。
        事实抽取与复盘沉淀一致（LLM 原子化，失败降级章节切片）；幂等键为
        (user_id, intent, query[:50])，防止同一对话多个 final 重复沉淀；
        content_hash 唯一键兜底内容级幂等。失败仅遍历到单条时告警，不抛出。

        Args:
            user_id: 业务用户 ID。
            intent: 路由意图（job/resume/tech/hr）。
            query: 触发沉淀的用户 query。
            response: 完整 final 文本。

        Returns:
            写入条数；非目标场景 / 响应过短 / 幂等命中 / 无记忆实例返回 None。
        """
        if intent not in ("job", "resume", "tech", "hr"):
            return None
        text = str(response or "").strip()
        if len(text) <= 200:
            return None
        if self._long_term_memory is None:
            return None
        key = (str(user_id), intent, str(query)[:50])
        if key in self._distilled_keys:
            logger.debug(
                "对话沉淀幂等命中，跳过: user_id={}, intent={}", user_id, intent
            )
            return None
        self._distilled_keys.add(key)

        interview = intent in ("tech", "hr")
        source = "模拟面试" if interview else "咨询对话"
        importance = 3 if interview else 2
        # LLM 原子化事实抽取（默认路径），失败 / 为空降级章节切片
        facts = await self._extract_facts_with_llm(text)
        sections = self._extract_review_sections(text)
        if facts:
            items = [(f["content"], int(f["type"])) for f in facts]
            llm_count = len(facts)
        else:
            items = [(content, memory_type) for content, memory_type in sections]
            llm_count = 0

        count = 0
        for content, memory_type in items:
            try:
                await self._long_term_memory.save(
                    user_id,
                    content,
                    memory_type=memory_type,
                    importance=importance,
                    source=source,
                )
                count += 1
            except Exception as exc:  # noqa: BLE001 - 单条失败不中断整体沉淀
                logger.warning("对话沉淀写入失败: {}", exc)
        if count:
            logger.info(
                "对话沉淀完成: user_id={}, intent={}, source={}, count={}, "
                "llm_facts={}, sections={}",
                user_id, intent, source, count, llm_count, len(sections),
            )
        return count or None

    def _make_agent_node(self, agent_name: str) -> Callable[[AgentState], Any]:
        """构建真实 Agent 节点（异步），统一装配记忆与 RAG。

        节点执行顺序：短期记忆读取（历史注入 state["messages"]）→
        RAG 上下文注入 → 注册表取 Agent 并执行 → 短期记忆回写
        （user + assistant 各一条）。记忆 / RAG 任一失败均不阻断生成。

        Args:
            agent_name: Agent 名称（job/resume/tech/hr）。

        Returns:
            LangGraph 异步节点函数。
        """

        async def node(state: AgentState) -> dict:
            user_id = state.get("user_id", "")
            # 输入清洗（注入防护：剔除控制字符/折叠空白/限长）
            state["user_input"] = self._sanitize_user_input(
                state.get("user_input", "")
            )
            query = state.get("user_input", "")

            # 1. 短期记忆注入（历史写进 state["messages"]，Agent 内部消费）
            if self._short_term_memory is not None:
                try:
                    history = await self._short_term_memory.get_messages(
                        user_id, limit=self._settings.short_term_max_messages
                    )
                    state["messages"] = history
                except Exception as exc:  # noqa: BLE001 - 记忆失败不阻断
                    logger.warning("短期记忆读取失败: {}", exc)

            # 2. RAG 检索注入
            rag_text = self._build_rag_context(agent_name, query)
            if rag_text:
                state["rag_context"] = rag_text

            # 2.5 长期记忆注入（跨会话沉淀，供提示词【用户长期记忆】区块消费；
            # 读取失败不阻断生成，置空上下文）
            if self._long_term_memory is not None and user_id:
                try:
                    memories = await self._long_term_memory.load(
                        user_id, limit=10, query=query or None
                    )
                    state["long_term_context"] = memories or []
                    logger.debug(
                        "长期记忆已读取: user_id={}, count={}",
                        user_id,
                        len(memories or []),
                    )
                except Exception as exc:  # noqa: BLE001 - 记忆失败不阻断
                    state["long_term_context"] = []
                    logger.warning("长期记忆读取失败: {}", exc)

            # 3. 执行 Agent（ReAct 版本：LLM 自主调用工具）
            agent = self._registry.get(agent_name)
            if agent is None:
                return {
                    "error": f"Agent {agent_name} 未注册",
                    "final_response": "系统内部错误，请稍后再试",
                }
            try:
                final_response = await agent.arun(state)
            except Exception as exc:  # noqa: BLE001 - 兜底，避免异常逃逸出图
                logger.exception("Agent[{}] 执行异常", agent_name)
                return {
                    "error": str(exc),
                    "final_response": "AI 服务执行失败，请稍后再试",
                }

            # 4. 短期记忆写入（user + assistant）
            if self._short_term_memory is not None and final_response:
                try:
                    await self._short_term_memory.add_message(
                        user_id, "user", query
                    )
                    await self._short_term_memory.add_message(
                        user_id, "assistant", final_response
                    )
                    # 标记当前会话 Agent，供后续无关键词轮次延续场景
                    await self._short_term_memory.set_active_agent(
                        user_id, agent_name
                    )
                except Exception as exc:  # noqa: BLE001 - 记忆失败不阻断
                    logger.warning("短期记忆写入失败: {}", exc)

            return {
                "final_response": final_response,
                "agent_name": agent_name,
                "rag_context": state.get("rag_context"),
                "llm_response": final_response,
            }

        return node

    async def run_stream(
        self, state: AgentState
    ) -> AsyncIterator[Dict[str, Any]]:
        """流式执行编排：路由 → 上下文装配 → Agent token 级流式 → 记忆回写。

        与 LangGraph 图（``ainvoke`` 批处理）共享路由 / 记忆 / RAG / Agent
        组件；token 级输出由本生成器路径承载，避免图框架在流式场景的额外
        开销。

        Args:
            state: 当前 AgentState（读取 user_id / user_input 等，执行中会
                写入 messages / rag_context 等上下文）。

        Yields:
            事件字典 ``{"type": ..., "data": ...}``，type 取值：

            - ``meta``：路由结果，data 为 {"intent", "agent"}；
            - ``chunk``：单个增量文本块，data 为 str；
            - ``final``：完整生成文本，data 为 str，每轮仅一次；
            - ``error``：友好错误提示，data 为 str，下发后终止。
        """
        # 0. 输入清洗（注入防护：剔除控制字符/折叠空白/限长，路由与各上下文共用）
        state["user_input"] = self._sanitize_user_input(state.get("user_input", ""))

        # 1. 路由（复用图内同一 router 节点逻辑，含会话延续）
        intent = (await self._router_node(state)).get("intent", "chat")
        yield {"type": "meta", "data": {"intent": intent, "agent": intent}}
        query = state.get("user_input", "")
        user_id = state.get("user_id", "")

        # 2. chat 兜底：直接流式自由问答，不读写短期记忆（与图内 chat 节点语义一致）
        if intent == "chat":
            try:
                llm = self._llm_factory.create_chat_llm("default")
            except ConfigError as exc:
                logger.warning("chat 流式模型初始化失败: {}", exc)
                yield {
                    "type": "error",
                    "data": "AI 服务未配置模型 Key，请联系管理员",
                }
                return
            content = ""
            try:
                async for chunk in llm.astream(query):
                    text = (
                        chunk.content
                        if hasattr(chunk, "content")
                        else str(chunk)
                    )
                    if not text:
                        continue
                    content += text
                    yield {"type": "chunk", "data": text}
            except Exception as exc:  # noqa: BLE001 - 流式异常统一转 error 事件
                logger.exception("chat 流式异常")
                yield {"type": "error", "data": "AI 服务调用失败，请稍后再试"}
                return
            yield {"type": "final", "data": content}
            return

        # 3. 真实 Agent：上下文装配（与 _make_agent_node 完全一致）
        agent = self._registry.get(intent)
        if agent is None:
            yield {"type": "error", "data": "系统内部错误，请稍后再试"}
            return
        if self._short_term_memory is not None:
            try:
                history = await self._short_term_memory.get_messages(
                    user_id, limit=self._settings.short_term_max_messages
                )
                state["messages"] = history
            except Exception as exc:  # noqa: BLE001 - 记忆失败不阻断
                logger.warning("短期记忆读取失败: {}", exc)
        rag_text = self._build_rag_context(intent, query)
        if rag_text:
            state["rag_context"] = rag_text

        # 3.5 长期记忆注入（跨会话沉淀，供提示词【用户长期记忆】区块消费；
        # 读取失败不阻断生成，置空上下文）
        if self._long_term_memory is not None and user_id:
            try:
                memories = await self._long_term_memory.load(
                    user_id, limit=10, query=query or None
                )
                state["long_term_context"] = memories or []
                logger.debug(
                    "已读取长期记忆: user_id={}, count={}",
                    user_id,
                    len(memories or []),
                )
            except Exception as exc:  # noqa: BLE001 - 记忆失败不阻断
                state["long_term_context"] = []
                logger.warning("长期记忆读取失败: {}", exc)

        # 4. Agent token 级流式生成（ReAct 版本；Agent 内部异常不自行捕获，
        # 此处统一兜底）
        content = ""
        try:
            async for chunk in agent.astream_run(state):
                content += chunk
                yield {"type": "chunk", "data": chunk}
        except Exception as exc:  # noqa: BLE001 - 流式异常统一转 error 事件
            logger.exception("Agent[{}] 流式执行异常", intent)
            yield {"type": "error", "data": "AI 服务执行失败，请稍后再试"}
            return

        # 5. 记忆回写（user + assistant + 当前会话 Agent 标记）
        if self._short_term_memory is not None and content:
            try:
                await self._short_term_memory.add_message(
                    user_id, "user", query
                )
                await self._short_term_memory.add_message(
                    user_id, "assistant", content
                )
                await self._short_term_memory.set_active_agent(
                    user_id, intent
                )
            except Exception as exc:  # noqa: BLE001 - 记忆失败不阻断
                logger.warning("短期记忆写入失败: {}", exc)

        yield {"type": "final", "data": content}

    def _chat_node(self, state: AgentState) -> dict:
        """自由问答兜底节点。

        调用默认模型直接回复用户输入；未配置模型 Key 时给出友好提示。

        Args:
            state: 当前 AgentState。

        Returns:
            更新结果 {"llm_response", "final_response"} 或错误结果。
        """
        # 创建默认模型（未配置 Key 时捕获并友好提示）
        try:
            llm = self._llm_factory.create_chat_llm("default")
        except ConfigError as exc:
            return {
                "error": str(exc),
                "final_response": "AI 服务未配置模型 Key，请联系管理员",
            }
        # 简单调用默认模型
        try:
            response = llm.invoke(state.get("user_input", "") or "")
            content = response.content if hasattr(response, "content") else str(response)
            return {"llm_response": content, "final_response": content}
        except Exception as exc:
            return {
                "error": str(exc),
                "final_response": "AI 服务调用失败，请稍后再试",
            }

    def _route_by_intent(self, state: AgentState) -> str:
        """按意图返回下一个节点名称。

        Args:
            state: 当前 AgentState。

        Returns:
            目标节点名称，默认 chat_agent。
        """
        return state.get("intent", "chat")

    def build(self) -> CompiledStateGraph:
        """构建并编译完整状态图。

        结构：``router → {job / resume / tech / hr / chat} → END``。

        Returns:
            编译后的 LangGraph 状态图。
        """
        graph = StateGraph(AgentState)
        # 注册路由节点与各真实 Agent 节点
        graph.add_node("router", self._router_node)
        graph.add_node("job_agent", self._make_agent_node("job"))
        graph.add_node("resume_agent", self._make_agent_node("resume"))
        graph.add_node("tech_agent", self._make_agent_node("tech"))
        graph.add_node("hr_agent", self._make_agent_node("hr"))
        graph.add_node("chat_agent", self._chat_node)
        # 入口为路由节点，按意图条件分发
        graph.set_entry_point("router")
        graph.add_conditional_edges(
            "router",
            self._route_by_intent,
            {
                "job": "job_agent",
                "resume": "resume_agent",
                "tech": "tech_agent",
                "hr": "hr_agent",
                "chat": "chat_agent",
            },
        )
        # 各 Agent 节点执行完成后终止
        graph.add_edge("job_agent", END)
        graph.add_edge("resume_agent", END)
        graph.add_edge("tech_agent", END)
        graph.add_edge("hr_agent", END)
        graph.add_edge("chat_agent", END)
        return graph.compile()
