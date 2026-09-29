"""记忆抽象基类。

定义记忆模块的统一接口（save / load / delete / close），
短期记忆（Redis）、长期记忆（MySQL + Milvus）均继承本接口，
使上层业务面向抽象编程，支持替换实现。
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    """记忆模块抽象接口。"""

    @abstractmethod
    async def save(self, user_id: str, content: Any, **kwargs: Any) -> None:
        """写入记忆。

        Args:
            user_id: 用户唯一标识。
            content: 记忆内容（消息 / 画像 / 事实等）。
            **kwargs: 附加参数（角色、时间戳、重要性等）。
        """

    @abstractmethod
    async def load(self, user_id: str, **kwargs: Any) -> Any:
        """读取记忆。

        Args:
            user_id: 用户唯一标识。
            **kwargs: 附加参数（数量限制、时间范围等）。

        Returns:
            记忆内容，无记忆时返回空容器（list / dict）。
        """

    @abstractmethod
    async def delete(self, user_id: str, **kwargs: Any) -> None:
        """删除记忆。

        Args:
            user_id: 用户唯一标识。
            **kwargs: 附加参数（删除范围等）。
        """

    @abstractmethod
    async def close(self) -> None:
        """释放底层连接资源。"""
