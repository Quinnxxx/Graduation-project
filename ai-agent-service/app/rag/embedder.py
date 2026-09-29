"""文本向量化器。

封装阿里云百炼 embedding 接口（OpenAI 兼容），提供单条与批量文本向量化。
客户端懒加载并缓存（同一进程复用 openai 客户端），减少不必要的连接创建；
批量接口按固定批大小调用以减少请求次数。
"""

from typing import List, Optional

from openai import OpenAI

from app.config.settings import Settings
from app.llm.factory import LLMFactory, get_llm_factory
from app.utils.exceptions import RAGError


class TextEmbedder:
    """文本向量化器：封装百炼 embedding 接口，提供单条与批量向量化。

    客户端懒加载并缓存（同一进程复用 openai 客户端），
    减少不必要的连接创建；批量接口按固定批大小调用以减少请求次数。
    """

    def __init__(
        self, settings: Settings, llm_factory: Optional[LLMFactory] = None
    ) -> None:
        """初始化向量化器。

        Args:
            settings: 全局配置（embedding_model / embedding_base_url / embedding_api_key）。
            llm_factory: LLM 客户端工厂，缺省使用全局单例。
        """
        self._settings = settings
        self._llm_factory = llm_factory or get_llm_factory()
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        """懒加载 embedding 客户端（幂等）。

        Returns:
            OpenAI 客户端实例。
        """
        if self._client is None:
            self._client = self._llm_factory.create_embedding()
        return self._client

    def embed_text(self, text: str) -> List[float]:
        """单条文本向量化。

        Args:
            text: 输入文本，不能为空。

        Returns:
            文本对应的向量（float 列表）。

        Raises:
            RAGError: 文本为空或向量化失败时。
        """
        if not text or not text.strip():
            raise RAGError("向量化文本不能为空")
        try:
            resp = self._get_client().embeddings.create(
                model=self._settings.embedding_model, input=text
            )
            return list(resp.data[0].embedding)
        except RAGError:
            raise
        except Exception as exc:
            raise RAGError("文本向量化失败", cause=exc) from exc

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量文本向量化（每批 16 条）。

        Args:
            texts: 文本列表。

        Returns:
            与输入顺序一致的向量列表。

        Raises:
            RAGError: 任一批次向量化失败时。
        """
        if not texts:
            return []
        result: List[List[float]] = []
        batch_size = 16
        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                resp = self._get_client().embeddings.create(
                    model=self._settings.embedding_model, input=batch
                )
                # openai 返回按输入顺序排列
                result.extend([list(item.embedding) for item in resp.data])
            return result
        except Exception as exc:
            raise RAGError("批量文本向量化失败", cause=exc) from exc
