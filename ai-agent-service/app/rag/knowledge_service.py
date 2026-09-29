"""知识库服务（RAG 核心）。

文档入库：分块 → 向量化 → Milvus 写入 → MySQL 元数据追踪；
检索：query 向量化后在 Milvus 按 COSINE 相似度召回；
删除：Milvus 向量与 MySQL 逻辑删除同步清理，保证两侧一致。

:class:`KnowledgeDocDAO` 为 knowledge_doc 表轻量数据访问（AI 服务内部使用，
pymysql 直连，不引入 ORM）；:class:`KnowledgeService` 编排完整流程。
"""

import random
import time
from typing import Any, Dict, List, Optional

import pymysql
from loguru import logger
from pymilvus import Collection

from app.config.settings import Settings
from app.rag.base import MilvusClient
from app.rag.chunker import TextChunker
from app.rag.embedder import TextEmbedder
from app.rag.reranker import Reranker
from app.utils.exceptions import RAGError


class KnowledgeDocDAO:
    """knowledge_doc 表轻量数据访问（仅 AI 服务内部使用，pymysql 直连）。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 DAO。

        Args:
            settings: 全局配置（mysql_*）。
        """
        self._settings = settings
        self._conn: Optional[pymysql.connections.Connection] = None

    def _get_conn(self) -> pymysql.connections.Connection:
        """懒加载 MySQL 连接（含断线重连保活）。

        Returns:
            pymysql 连接对象。

        Raises:
            RAGError: 连接失败时。
        """
        try:
            if self._conn is None:
                self._conn = pymysql.connect(
                    host=self._settings.mysql_host,
                    port=self._settings.mysql_port,
                    user=self._settings.mysql_username,
                    password=self._settings.mysql_password,
                    database=self._settings.mysql_database,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True,
                )
            else:
                self._conn.ping(reconnect=True)  # 保活：断线自动重连
            return self._conn
        except Exception as exc:
            raise RAGError("MySQL 连接失败", cause=exc) from exc

    def new_id(self) -> int:
        """生成雪花风格 64 位主键（毫秒时间戳 + 随机位，与业务服务风格一致）。

        Returns:
            64 位整数主键。
        """
        return (int(time.time() * 1000) << 22) | random.getrandbits(22)

    def insert_doc(
        self,
        doc_id: int,
        doc_title: str,
        doc_type: int,
        content: str,
        chunk_count: int,
        source: str,
    ) -> None:
        """新增或更新文档元数据（幂等 upsert）。

        同 doc_id 重复入库时按主键更新元数据并恢复逻辑删除标记，
        与 index_doc 的幂等语义（先清旧向量再写入）保持一致。

        Args:
            doc_id: 主键。
            doc_title: 标题。
            doc_type: 文档类型 1-5。
            content: 原文。
            chunk_count: 分块数。
            source: 来源。
        """
        sql = (
            "INSERT INTO knowledge_doc (id, doc_title, doc_type, content, chunk_count, vector_status, source, is_deleted) "
            "VALUES (%s, %s, %s, %s, %s, 1, %s, 0) "
            "ON DUPLICATE KEY UPDATE "
            "doc_title=VALUES(doc_title), doc_type=VALUES(doc_type), content=VALUES(content), "
            "chunk_count=VALUES(chunk_count), vector_status=1, source=VALUES(source), is_deleted=0"
        )
        try:
            with self._get_conn().cursor() as cursor:
                cursor.execute(sql, (doc_id, doc_title, doc_type, content, chunk_count, source))
        except Exception as exc:
            raise RAGError("知识库元数据写入失败", cause=exc) from exc

    def update_vector_status(self, doc_id: int, chunk_count: int) -> None:
        """更新向量化状态与分块数。

        Args:
            doc_id: 文档主键。
            chunk_count: 分块数。
        """
        sql = "UPDATE knowledge_doc SET vector_status=1, chunk_count=%s WHERE id=%s AND is_deleted=0"
        try:
            with self._get_conn().cursor() as cursor:
                cursor.execute(sql, (chunk_count, doc_id))
        except Exception as exc:
            raise RAGError("知识库向量状态更新失败", cause=exc) from exc

    def mark_deleted(self, doc_id: int) -> None:
        """逻辑删除文档。

        Args:
            doc_id: 文档主键。
        """
        sql = "UPDATE knowledge_doc SET is_deleted=1 WHERE id=%s"
        try:
            with self._get_conn().cursor() as cursor:
                cursor.execute(sql, (doc_id,))
        except Exception as exc:
            raise RAGError("知识库逻辑删除失败", cause=exc) from exc

    def get_doc(self, doc_id: int) -> Optional[Dict]:
        """查询未删除文档详情。

        Args:
            doc_id: 文档主键。

        Returns:
            文档行字典，不存在返回 None。
        """
        sql = (
            "SELECT id, doc_title, doc_type, content, chunk_count, vector_status, source, create_time "
            "FROM knowledge_doc WHERE id=%s AND is_deleted=0"
        )
        try:
            with self._get_conn().cursor() as cursor:
                cursor.execute(sql, (doc_id,))
                return cursor.fetchone()
        except Exception as exc:
            raise RAGError("知识库文档查询失败", cause=exc) from exc

    def list_docs(
        self, page: int, page_size: int, doc_type: Optional[int] = None
    ) -> Dict:
        """分页查询未删除文档。

        Args:
            page: 页码（从 1 开始）。
            page_size: 每页条数。
            doc_type: 可选文档类型过滤。

        Returns:
            {"total": int, "records": [行字典...]}，按 create_time 倒序。
        """
        where = "WHERE is_deleted=0"
        params: List[Any] = []
        if doc_type is not None:
            where += " AND doc_type=%s"
            params.append(doc_type)
        try:
            with self._get_conn().cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM knowledge_doc {where}", params)
                total = cursor.fetchone()["cnt"]
                cursor.execute(
                    f"SELECT id, doc_title, doc_type, content, chunk_count, vector_status, source, create_time "
                    f"FROM knowledge_doc {where} ORDER BY create_time DESC LIMIT %s OFFSET %s",
                    params + [page_size, (page - 1) * page_size],
                )
                records = cursor.fetchall()
            return {"total": total, "records": records}
        except Exception as exc:
            raise RAGError("知识库分页查询失败", cause=exc) from exc

    def close(self) -> None:
        """关闭连接（幂等）。"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None

    # 注意：f-string 拼接的 SQL 中 where 子句来自内部常量拼接（无用户输入直接进入），
    # 参数全部走 %s 占位符，满足防注入要求


class KnowledgeService:
    """知识库服务：文档入库（分块→向量化→Milvus）与检索、删除、列表。

    流程说明：文本先分块，再批量向量化写入 Milvus，MySQL 记录元数据并
    追踪 vector_status / chunk_count；删除时向量与元数据同步清理，
    保证检索结果与文档列表一致。

    检索采用两阶段（向量召回 + Rerank 精排），vector_score 保留原始
    相似度供对比实验；Rerank 失败自动降级为向量排序。
    """

    def __init__(self, settings: Settings, milvus_client: MilvusClient) -> None:
        """初始化知识库服务。

        Args:
            settings: 全局配置。
            milvus_client: Milvus 客户端（由 main 生命周期注入）。
        """
        self._settings = settings
        self._milvus = milvus_client
        self._embedder = TextEmbedder(settings)
        self._reranker = Reranker(settings)
        self._chunker = TextChunker()
        self._dao = KnowledgeDocDAO(settings)

    def ensure_collection(self) -> None:
        """确保 Milvus 集合存在（不存在则按 schema 创建并加载）。

        Schema 设计：主键 id 由 Milvus 自动分配（auto_id），
        doc_id + chunk_index 标识业务文档块；向量字段维度取配置 embedding_dim；
        索引 HNSW + COSINE 适合中文语义检索。
        """
        name = self._settings.milvus_collection
        if self._milvus.has_collection(name):
            return
        from pymilvus import CollectionSchema, DataType, FieldSchema, Index

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="doc_title", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="doc_type", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self._settings.embedding_dim,
            ),
        ]
        schema = CollectionSchema(fields, description="校招求职知识库向量集合")
        collection = Collection(name, schema, using=self._settings.milvus_alias)
        index = Index(
            collection,
            "embedding",
            {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
        )
        collection.load()
        logger.info("Milvus 集合创建完成: {}, dim={}", name, self._settings.embedding_dim)

    def _get_collection(self) -> Collection:
        """懒获取集合并确保已加载。

        Returns:
            Milvus Collection 实例。
        """
        self.ensure_collection()
        collection = Collection(
            self._settings.milvus_collection, using=self._settings.milvus_alias
        )
        try:
            if not collection.is_loaded:
                collection.load()
        except Exception:
            pass
        return collection

    def _delete_vectors(self, doc_id: int) -> None:
        """仅删除 Milvus 中该 doc_id 的全部向量（幂等清理，不触碰 MySQL）。

        Args:
            doc_id: 文档主键。
        """
        try:
            self._get_collection().delete(expr=f'doc_id in ["{doc_id}"]')
        except Exception as exc:
            raise RAGError("知识向量删除失败", cause=exc) from exc

    def index_doc(
        self,
        doc_id: int,
        doc_title: str,
        doc_type: int,
        content: str,
        source: str = "用户上传",
    ) -> int:
        """知识文档入库：分块→向量化→Milvus 写入→MySQL 元数据更新。

        幂等：同 doc_id 重复入库先清旧向量再写入，避免向量残留。

        Args:
            doc_id: 文档主键（雪花 id，由调用方生成或传入）。
            doc_title: 文档标题。
            doc_type: 文档类型 1-5。
            content: 文档原文。
            source: 来源说明。

        Returns:
            分块数量。

        Raises:
            RAGError: 内容为空或任一步骤失败时。
        """
        if not content or not content.strip():
            raise RAGError("文档内容为空")
        # 幂等清理旧向量（同 doc_id 重复入库不残留）
        try:
            self._delete_vectors(doc_id)
        except RAGError:
            pass  # 首次入库无旧向量，忽略
        chunks = self._chunker.chunk(content)
        if not chunks:
            raise RAGError("文档分块结果为空")
        vectors = self._embedder.embed_texts(chunks)
        data = [
            {
                "doc_id": str(doc_id),
                "doc_title": doc_title,
                "doc_type": doc_type,
                "content": chunk,
                "chunk_index": idx,
                "embedding": vec,
            }
            for idx, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        try:
            self._get_collection().insert(data)
            self._get_collection().flush()
        except Exception as exc:
            raise RAGError("知识向量入库失败", cause=exc) from exc
        # MySQL 元数据（插入新行 + 标记已向量化）
        self._dao.insert_doc(doc_id, doc_title, doc_type, content, len(chunks), source)
        logger.info("知识入库完成: doc_id={}, chunks={}", doc_id, len(chunks))
        return len(chunks)

    def create_doc(
        self,
        doc_title: str,
        doc_type: int,
        content: str,
        source: str = "用户上传",
    ) -> int:
        """创建知识文档：生成主键并走完整入库流程。

        Args:
            doc_title: 文档标题。
            doc_type: 文档类型 1-5。
            content: 文档原文。
            source: 来源说明。

        Returns:
            生成的文档主键 doc_id。
        """
        doc_id = self._dao.new_id()
        self.index_doc(doc_id, doc_title, doc_type, content, source)
        return doc_id

    def delete_doc(self, doc_id: int) -> None:
        """删除知识文档：Milvus 向量 + MySQL 逻辑删除，保持两侧一致。

        Args:
            doc_id: 文档主键。
        """
        self._delete_vectors(doc_id)
        self._dao.mark_deleted(doc_id)
        logger.info("知识删除完成: doc_id={}", doc_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[int] = None,
        enable_rerank: bool = True,
    ) -> List[Dict]:
        """两阶段检索：向量召回（粗排）→ Rerank 精排。

        阶段1 向量召回 top_k*3 条（上限 30），保证召回率；
        阶段2 由 Reranker 按语义相关性精排取 top_k，修正词面重叠干扰。
        Rerank 失败自动降级为向量排序（不阻断检索）。

        Args:
            query: 查询文本。
            top_k: 最终返回条数。
            doc_type: 可选按文档类型过滤。
            enable_rerank: 是否启用精排（False 时仅向量召回，供对比实验）。

        Returns:
            [{doc_id, doc_title, doc_type, content, chunk_index, vector_score, score}]，
            score 为最终排序分（精排后为 relevance_score，否则等于 vector_score），
            按 score 降序。
        """
        if not query or not query.strip():
            raise RAGError("查询内容为空")
        query_vec = self._embedder.embed_text(query)
        # 阶段1：向量召回（粗排），召回量为 top_k 的 3 倍，上限 30
        recall_k = min(top_k * 3, 30)
        expr = f"doc_type == {doc_type}" if doc_type is not None else None
        try:
            results = self._get_collection().search(
                data=[query_vec],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=recall_k,
                expr=expr,
                output_fields=["doc_id", "doc_title", "doc_type", "content", "chunk_index"],
            )
        except Exception as exc:
            raise RAGError("知识检索失败", cause=exc) from exc
        items: List[Dict] = []
        for hit in results[0]:
            items.append(
                {
                    "doc_id": hit.entity.get("doc_id"),
                    "doc_title": hit.entity.get("doc_title"),
                    "doc_type": hit.entity.get("doc_type"),
                    "content": hit.entity.get("content"),
                    "chunk_index": hit.entity.get("chunk_index"),
                    "vector_score": round(hit.distance, 4),
                }
            )
        if not items:
            return []
        # 阶段2：Rerank 精排（失败自动降级为向量排序）
        if enable_rerank:
            try:
                documents = [item["content"] for item in items]
                scores = self._reranker.rerank(query, documents, top_n=top_k)
                for item, score in zip(items, scores):
                    item["score"] = round(score, 4)
                items.sort(key=lambda x: x["score"], reverse=True)
            except RAGError as exc:
                logger.warning("Rerank 精排失败，降级为向量排序: {}", exc.message)
                for item in items:
                    item["score"] = item["vector_score"]
                items.sort(key=lambda x: x["score"], reverse=True)
        else:
            for item in items:
                item["score"] = item["vector_score"]
            items.sort(key=lambda x: x["score"], reverse=True)
        return items[:top_k]

    def list_docs(self, page: int, page_size: int, doc_type: Optional[int] = None) -> Dict:
        """分页列表（透传 DAO）。

        Args:
            page: 页码。
            page_size: 每页条数。
            doc_type: 可选文档类型过滤。

        Returns:
            {"total": int, "records": [...]}。
        """
        return self._dao.list_docs(page, page_size, doc_type)

    def get_doc(self, doc_id: int) -> Optional[Dict]:
        """文档详情（透传 DAO）。

        Args:
            doc_id: 文档主键。

        Returns:
            文档行字典，不存在返回 None。
        """
        return self._dao.get_doc(doc_id)

    def close(self) -> None:
        """释放资源（幂等）。"""
        self._dao.close()
