"""两阶段检索精排器。

向量召回（粗排）易受词面重叠干扰（如"技术一面"与"面试"字面重合但
语义相关性低），Rerank 基于 query 与候选文档的语义相关性精排，
显著提升 Top-N 准确率。本类仅负责调用百炼 rerank 接口，失败降级
由调用方（KnowledgeService.search）处理。
"""

import requests
from typing import List, Optional

from loguru import logger

from app.config.settings import Settings
from app.utils.exceptions import RAGError


class Reranker:
    """基于阿里云百炼 rerank 模型的精排器。"""

    def __init__(self, settings: Settings) -> None:
        """初始化精排器。

        Args:
            settings: 全局配置（rerank_model / rerank_url / dashscope_api_key）。
        """
        self._settings = settings

    def rerank(
        self, query: str, documents: List[str], top_n: Optional[int] = None
    ) -> List[float]:
        """对候选文档重排，返回与输入顺序一致的 relevance_score 列表。

        调用百炼原生 rerank 接口（非 OpenAI 兼容），按响应中 index
        映射回输入顺序，保证调用方可以直接按序使用。

        Args:
            query: 查询文本。
            documents: 候选文档文本列表。
            top_n: 返回的相关性分数条数上限（按相关度排序后取前 N），缺省全量。

        Returns:
            与 documents 输入顺序一一对应的相关性分数列表（0.0~1.0）。

        Raises:
            RAGError: documents 为空、未配置 key、接口异常或响应解析失败时。
        """
        if not documents:
            return []
        cfg = self._settings.get_rerank_config()
        if not cfg["api_key"]:
            raise RAGError("未配置 Rerank API Key（复用百炼 dashscope_api_key）")
        top_n = top_n or len(documents)
        payload = {
            "model": cfg["model"],
            "input": {"query": query, "documents": documents},
            "parameters": {"top_n": top_n},
        }
        logger.debug(
            "Rerank 请求: query={}, docs={}, top_n={}", query, len(documents), top_n
        )
        try:
            resp = requests.post(
                cfg["url"],
                headers={
                    "Authorization": f"Bearer {cfg['api_key']}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
        except Exception as exc:
            raise RAGError("Rerank 接口调用失败", cause=exc) from exc
        if resp.status_code != 200:
            raise RAGError(
                f"Rerank 接口返回异常: HTTP {resp.status_code}, {resp.text[:200]}"
            )
        try:
            data = resp.json()
            results = data["output"]["results"]
        except Exception as exc:
            raise RAGError("Rerank 响应解析失败", cause=exc) from exc
        # 响应按相关度降序返回，需按 index 映射回输入顺序
        scores: List[float] = [0.0] * len(documents)
        for item in results:
            index = item.get("index")
            score = item.get("relevance_score", 0.0)
            if index is not None and 0 <= index < len(scores):
                scores[index] = score
        logger.debug(
            "Rerank 完成: top_score={}, docs={}", max(scores) if scores else 0.0, len(scores)
        )
        return scores
