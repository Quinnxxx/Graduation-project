"""RAG 检索引擎基类与 Milvus 连接封装。

:class:`MilvusClient` 负责 Milvus 连接的懒加载、健康检查与集合管理；
:class:`RAGBase` 定义检索/写入的标准接口，具体检索引擎（简历检索、
岗位检索、知识库问答）继承实现。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from loguru import logger
from pymilvus import Collection, connections, utility

from app.config.settings import Settings
from app.utils.exceptions import RAGError


class MilvusClient:
    """Milvus 连接封装。

    支持懒连接（首次使用时建立）、显式关闭与集合级操作。
    所有外部调用均捕获异常并包装为 :class:`RAGError`。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化 Milvus 客户端。

        Args:
            settings: 全局配置（milvus_host / milvus_port / milvus_alias 等）。
        """
        self._settings = settings
        self._connected: bool = False

    def connect(self) -> None:
        """建立与 Milvus 的连接（幂等，已连接则直接返回）。

        Raises:
            RAGError: 连接失败时。
        """
        if self._connected:
            return
        kwargs: Dict[str, Any] = {
            "alias": self._settings.milvus_alias,
            "host": self._settings.milvus_host,
            "port": self._settings.milvus_port,
        }
        if self._settings.milvus_username:
            kwargs["user"] = self._settings.milvus_username
            kwargs["password"] = self._settings.milvus_password
        try:
            connections.connect(**kwargs)
            self._connected = True
            logger.info(
                "Milvus 连接成功: host={}, port={}",
                self._settings.milvus_host,
                self._settings.milvus_port,
            )
        except Exception as exc:
            self._connected = False
            raise RAGError("Milvus 连接失败", cause=exc) from exc

    def close(self) -> None:
        """断开与 Milvus 的连接（幂等）。"""
        if not self._connected:
            return
        try:
            connections.disconnect(self._settings.milvus_alias)
        except Exception as exc:
            logger.warning("Milvus 断开连接异常: {}", exc)
        finally:
            self._connected = False

    @property
    def is_connected(self) -> bool:
        """返回当前连接状态。

        Returns:
            已连接返回 True。
        """
        return self._connected

    def has_collection(self, name: str) -> bool:
        """判断集合是否存在。

        Args:
            name: 集合名称。

        Returns:
            存在返回 True。

        Raises:
            RAGError: 元数据查询失败时。
        """
        self.connect()
        try:
            return utility.has_collection(name, using=self._settings.milvus_alias)
        except Exception as exc:
            raise RAGError(f"检查 Milvus 集合失败: {name}", cause=exc) from exc

    def get_collection(self, name: str) -> Collection:
        """获取集合对象（调用方负责集合 schema 与索引的保证）。

        Args:
            name: 集合名称。

        Returns:
            Milvus Collection 实例。

        Raises:
            RAGError: 集合不存在或获取失败时。
        """
        self.connect()
        try:
            return Collection(name, using=self._settings.milvus_alias)
        except Exception as exc:
            raise RAGError(f"获取 Milvus 集合失败: {name}", cause=exc) from exc

    def __enter__(self) -> "MilvusClient":
        """上下文管理器入口：自动建立连接。"""
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        """上下文管理器出口：自动断开连接。"""
        self.close()


class RAGBase(ABC):
    """RAG 检索引擎抽象基类。

    定义检索（:meth:`search`）、写入（:meth:`insert`）、删除（:meth:`delete`）
    与向量化（:meth:`embed_text`）标准接口。具体实现通过依赖注入方式
    接收 milvus 客户端与向量化器，避免与具体模型/集合耦合。
    """

    def __init__(
        self,
        settings: Settings,
        milvus_client: Optional[MilvusClient] = None,
        embedder: Optional[Any] = None,
    ) -> None:
        """初始化 RAG 引擎。

        Args:
            settings: 全局配置。
            milvus_client: Milvus 客户端，缺省自动创建。
            embedder: 向量化器（实现 embed_text 语义的对象），缺省为 None。
        """
        self._settings = settings
        self._milvus = milvus_client or MilvusClient(settings)
        self._embedder = embedder

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """将文本向量化。

        Args:
            text: 输入文本。

        Returns:
            文本对应的向量（float 列表）。
        """

    @abstractmethod
    def search(self, query: str, top_k: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        """执行向量检索。

        Args:
            query: 查询文本。
            top_k: 返回结果数量。
            **kwargs: 检索过滤条件（如 user_id、job_id 等分区字段）。

        Returns:
            检索结果文档列表（按相似度降序）。
        """

    @abstractmethod
    def insert(self, documents: List[Dict[str, Any]]) -> None:
        """批量写入文档。

        Args:
            documents: 文档列表，每个文档需包含向量字段与元数据字段。
        """

    @abstractmethod
    def delete(self, doc_ids: List[str]) -> None:
        """按主键批量删除文档。

        Args:
            doc_ids: 文档主键列表。
        """
