"""短期会话记忆：基于 Redis 实现，支持滑动窗口与过期清理。

存储结构：Redis List（独立 db 隔离），元素为 JSON 字符串
（role / content / timestamp）。

- 滑动窗口：每次写入裁剪至最近 ``short_term_max_messages`` 条；
- 过期清理：每次读写续期 TTL（``short_term_ttl`` 秒），超时由 Redis 自动回收。
"""

import json
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from loguru import logger

from app.config.settings import Settings
from app.memory.base import BaseMemory
from app.utils.exceptions import MemoryError

# Redis Key 模板：ai-agent:short_term:{user_id}
_KEY_PATTERN = "ai-agent:short_term:{user_id}"
# Redis Key 模板：ai-agent:active_agent:{user_id}（记录用户当前会话 Agent，供多轮路由延续）
_ACTIVE_KEY_PATTERN = "ai-agent:active_agent:{user_id}"
# 场景标记 TTL（秒）：2 小时。
# 现状 30 分钟对"面试中途长时间停顿（如隔几小时回来继续）"不够，会误落 chat；
# 但也不能直接对齐 short_term_ttl(86400)：24 小时会让用户次日无论在哪个页面
# （含通用 AI 助手）只要没说强短语就被延续进面试场景，造成场景粘连。
# Redis 长期失效后的跨天续面由 _warm_rebuild_if_needed（本批文件 7）从持久化历史重建兜底。
_ACTIVE_TTL = 7200


class ShortTermMemory(BaseMemory):
    """短期会话记忆（Redis List 实现）。"""

    def __init__(self, settings: Settings) -> None:
        """初始化短期记忆客户端。

        Args:
            settings: 全局配置（redis_host / redis_port / redis_short_term_db 等）。

        Raises:
            MemoryError: Redis 客户端创建失败时。
        """
        self._settings = settings
        self._client = self._build_client()

    def _build_client(self) -> aioredis.Redis:
        """构建 Redis 异步客户端。

        Returns:
            Redis 异步客户端（decode_responses=True，直接返回字符串）。

        Raises:
            MemoryError: 客户端创建失败时。
        """
        password = self._settings.redis_password
        auth = f":{password}@" if password else ""
        url = (
            f"redis://{auth}{self._settings.redis_host}:"
            f"{self._settings.redis_port}/{self._settings.redis_short_term_db}"
        )
        try:
            return aioredis.from_url(url, decode_responses=True)
        except Exception as exc:
            raise MemoryError("Redis 客户端创建失败", cause=exc) from exc

    def _key(self, user_id: str) -> str:
        """生成用户会话 Key。

        Args:
            user_id: 用户唯一标识。

        Returns:
            Redis Key。
        """
        return _KEY_PATTERN.format(user_id=user_id)

    async def add_message(self, user_id: str, role: str, content: str) -> None:
        """追加一条会话消息，并执行滑动窗口裁剪与 TTL 续期。

        Args:
            user_id: 用户唯一标识。
            role: 消息角色（user / assistant / system）。
            content: 消息内容。

        Raises:
            MemoryError: 写入失败时。
        """
        payload = json.dumps(
            {"role": role, "content": content, "ts": int(time.time())},
            ensure_ascii=False,
        )
        key = self._key(user_id)
        try:
            length = await self._client.rpush(key, payload)
            max_len = self._settings.short_term_max_messages
            if length > max_len:
                # 滑动窗口：仅保留最近 max_len 条
                await self._client.ltrim(key, length - max_len, -1)
            await self._client.expire(key, self._settings.short_term_ttl)
        except Exception as exc:
            raise MemoryError(
                f"短期记忆写入失败: user_id={user_id}", cause=exc
            ) from exc

    async def get_messages(
        self, user_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """读取会话消息（时间正序，旧 -> 新）。

        Args:
            user_id: 用户唯一标识。
            limit: 返回最近 N 条，None 返回全部。

        Returns:
            消息字典列表 [{role, content, ts}, ...]。

        Raises:
            MemoryError: 读取失败时。
        """
        key = self._key(user_id)
        try:
            raw_list = await self._client.lrange(key, 0, -1)
            messages: List[Dict[str, Any]] = [
                json.loads(raw) for raw in raw_list
            ]
            if limit is not None:
                messages = messages[-limit:]
            # 读取即续期
            await self._client.expire(key, self._settings.short_term_ttl)
            return messages
        except Exception as exc:
            raise MemoryError(
                f"短期记忆读取失败: user_id={user_id}", cause=exc
            ) from exc

    def _active_key(self, user_id: str) -> str:
        """生成用户当前会话 Agent 标记 Key。

        Args:
            user_id: 用户唯一标识。

        Returns:
            Redis Key。
        """
        return _ACTIVE_KEY_PATTERN.format(user_id=user_id)

    async def set_active_agent(self, user_id: str, agent_name: str) -> None:
        """记录用户当前会话所属 Agent（用于多轮对话的意图延续）。

        显式切换场景（如从技术面试转到简历优化）由路由关键词优先识别并
        覆盖本标记；标记带 TTL，会话静默超时后自动失效，回落到 chat 兜底。

        Args:
            user_id: 用户唯一标识。
            agent_name: Agent 名称（job/resume/tech/hr）。

        Raises:
            MemoryError: 写入失败时。
        """
        try:
            await self._client.set(
                self._active_key(user_id), agent_name, ex=_ACTIVE_TTL
            )
        except Exception as exc:
            raise MemoryError(
                f"当前会话 Agent 写入失败: user_id={user_id}", cause=exc
            ) from exc

    async def get_active_agent(self, user_id: str) -> Optional[str]:
        """读取用户当前会话所属 Agent。

        Args:
            user_id: 用户唯一标识。

        Returns:
            Agent 名称；无有效标记时返回 None。
        """
        try:
            return await self._client.get(self._active_key(user_id))
        except Exception as exc:
            # 读取失败不阻断主流程，按无会话上下文处理（回落规则路由/chat）
            logger.warning("当前会话 Agent 读取失败: {}", exc)
            return None

    async def clear_active_agent(self, user_id: str) -> None:
        """清除用户当前会话 Agent 标记。

        业务语义：用户退出某场景（如完成面试复盘 / 自由问答）后可清除
        延续标记，使下一条请求不再被旧场景延续劫持。

        Args:
            user_id: 用户唯一标识。

        Raises:
            MemoryError: 删除失败时；无标记时静默成功。
        """
        try:
            await self._client.delete(self._active_key(user_id))
        except Exception as exc:
            raise MemoryError(
                f"当前会话 Agent 清除失败: user_id={user_id}", cause=exc
            ) from exc

    async def save(self, user_id: str, content: Any, **kwargs: Any) -> None:
        """实现 BaseMemory.save：追加一条消息。

        Args:
            user_id: 用户唯一标识。
            content: 消息内容（非字符串将 str() 转换）。
            **kwargs: 支持 role 参数（默认 user）。
        """
        role = kwargs.get("role", "user")
        await self.add_message(user_id, role, str(content))

    async def load(self, user_id: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """实现 BaseMemory.load：读取会话消息。

        Args:
            user_id: 用户唯一标识。
            **kwargs: 支持 limit 参数。

        Returns:
            消息字典列表。
        """
        return await self.get_messages(user_id, limit=kwargs.get("limit"))

    async def delete(self, user_id: str, **kwargs: Any) -> None:
        """实现 BaseMemory.delete：删除用户全部短期会话。

        Args:
            user_id: 用户唯一标识。
            **kwargs: 预留。

        Raises:
            MemoryError: 删除失败时。
        """
        try:
            await self._client.delete(
                self._key(user_id), self._active_key(user_id)
            )
        except Exception as exc:
            raise MemoryError(
                f"短期记忆删除失败: user_id={user_id}", cause=exc
            ) from exc

    async def ping(self) -> bool:
        """探测 Redis 连通性（供健康检查使用）。

        Returns:
            连通返回 True。
        """
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def clear_expired(self) -> int:
        """清理过期会话（接口占位）。

        Redis 由 TTL 自动回收过期 Key，本方法仅保留接口
        供后续批量清理 / 统计扩展。

        Returns:
            本次清理数量（当前恒为 0）。
        """
        return 0

    async def close(self) -> None:
        """关闭 Redis 连接（幂等）。"""
        try:
            await self._client.aclose()
        except Exception as exc:
            raise MemoryError("短期记忆连接关闭失败", cause=exc) from exc
