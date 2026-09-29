"""长期用户记忆：MySQL 原文落库 + Milvus 语义向量双写。

论文"长期记忆"模块的数据载体，与短期记忆（Redis 会话窗口）、工作记忆
（LangGraph State 单轮上下文）互补：

- ``short_term``（Redis）：当前会话的滑动消息窗口，TTL 内延续场景；
- ``working``（LangGraph State）：单轮执行内的状态传递；
- ``long_term``（本模块，MySQL + Milvus）：跨会话沉淀的用户事实 / 画像 /
  技能 / 面试教训，支持按用户分区做语义检索与结构化读取。

实现要点：
- MySQL :class:`user_memory` 表存原文与元数据（memory_type/importance/
  source/vector_status），逻辑删除，供结构化解读；
- Milvus 独立集合（``campus_recruit_user_memory``）保存内容向量，按
  user_id 分区写入，供语义召回；
- 双写一致：先向量入库（Milvus），再落 MySQL（vector_status=1）；
  Milvus 侧失败仅告警降级（原文仍落 MySQL，vector_status=0），MySQL
  失败向上抛错——不因向量侧故障丢失记忆原文。

所有外部调用（MySQL / Milvus / Embedding）异常统一包装为
:class:`RAGError`，读取失败不阻断上层（返回空列表）。
"""

import hashlib
import random
import time
from typing import Any, Dict, List, Optional

import pymysql
from loguru import logger
from pymilvus import Collection
from pymysql.err import IntegrityError

from app.config.settings import Settings
from app.memory.base import BaseMemory
from app.rag.base import MilvusClient
from app.rag.embedder import TextEmbedder
from app.utils.exceptions import RAGError


class LongTermMemory(BaseMemory):
    """长期用户记忆：MySQL + Milvus 双写实现。

    Attributes:
        _settings: 全局配置（mysql_* / milvus_* / embedding_dim）。
        _milvus: Milvus 客户端。
        _embedder: 文本向量化器。
        _conn: pymysql 懒连接（None 表示尚未建立）。
    """

    def __init__(
        self,
        settings: Settings,
        milvus_client: Optional[MilvusClient] = None,
        embedder: Optional[TextEmbedder] = None,
    ) -> None:
        """初始化长期记忆模块。

        Args:
            settings: 全局配置（mysql_* / milvus_* / embedding_*）。
            milvus_client: Milvus 客户端，缺省自动创建。
            embedder: 文本向量化器，缺省自动创建。
        """
        self._settings = settings
        self._milvus = milvus_client or MilvusClient(settings)
        self._embedder = embedder or TextEmbedder(settings)
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

    def _new_id(self) -> int:
        """生成雪花风格 64 位主键（毫秒时间戳 + 随机位）。

        Returns:
            64 位整数主键。
        """
        return (int(time.time() * 1000) << 22) | random.getrandbits(22)

    def _ensure_collection(self) -> None:
        """确保长期记忆 Milvus 集合存在（不存在则按 schema 创建并加载）。

        Schema 设计：Milvus 自增主键 id + 业务记忆主键 memory_id（对应
        user_memory.id）+ user_id 分区 + content 原文 + embedding 向量；
        索引 HNSW + COSINE 适合中文语义检索，向量维度取配置 embedding_dim。
        """
        name = self._settings.milvus_user_memory_collection
        if self._milvus.has_collection(name):
            return
        from pymilvus import CollectionSchema, DataType, FieldSchema, Index

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="memory_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self._settings.embedding_dim,
            ),
        ]
        schema = CollectionSchema(fields, description="长期用户记忆向量集合")
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
        logger.info(
            "Milvus 长期记忆集合创建完成: {}, dim={}",
            name,
            self._settings.embedding_dim,
        )

    def _get_collection(self) -> Collection:
        """懒获取集合并确保已加载。

        Returns:
            Milvus Collection 实例。
        """
        self._ensure_collection()
        collection = Collection(
            self._settings.milvus_user_memory_collection,
            using=self._settings.milvus_alias,
        )
        try:
            if not collection.is_loaded:
                collection.load()
        except Exception:
            pass
        return collection

    async def save(
        self, user_id: str, content: Any, **kwargs: Any
    ) -> None:
        """写入一条长期记忆（相似度去重 → Milvus 向量先入 → MySQL 原文落库）。

        升级语义：
        1. 相似度去重：dedup_threshold（默认 0.90，>0 生效）先把内容向量化，
           对该用户既有向量做 COSINE 召回（limit=3）；最高相似度 >= 阈值判为
           重复，仅日志 "相似记忆已存在" 并直接返回，不落库不插向量；
        2. 跨进程幂等：content_hash = 内容 MD5，配合 user_memory.uk_user_hash
           唯一键，重复 save 命中 MySQL IntegrityError(1062) 时按已存在跳过
           不抛错（进程重启后同 query 也不重复沉淀）；
        3. 双写降级语义保持不变：Milvus 失败仅告警（vector_status=0 仍落
           MySQL），MySQL 写入失败（非 1062）向上抛错。

        Args:
            user_id: 用户唯一标识。
            content: 记忆内容。
            **kwargs: 支持 memory_type（默认5）/ importance（默认2）/
                source（默认"自由问答"）/ dedup_threshold（默认0.90）。

        Raises:
            RAGError: 内容为空或 MySQL 写入失败（非 1062 重复）时。
        """
        text = str(content).strip()
        if not text:
            raise RAGError("记忆内容为空")
        memory_type = int(kwargs.get("memory_type", 5))
        importance = int(kwargs.get("importance", 2))
        source = str(kwargs.get("source", "自由问答"))
        dedup_threshold = float(kwargs.get("dedup_threshold", 0.90))
        content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

        # 1. 相似度去重（命中即放弃本次写入；向量化/召回失败仅告警不阻断）
        if dedup_threshold > 0:
            try:
                vector = self._embedder.embed_text(text)
                hits = self._get_collection().search(
                    data=[vector],
                    anns_field="embedding",
                    param={"metric_type": "COSINE", "params": {"ef": 64}},
                    limit=3,
                    expr=f'user_id == "{user_id}"',
                    output_fields=["memory_id", "content"],
                )
                if hits and hits[0] and hits[0][0].distance >= dedup_threshold:
                    logger.info(
                        "相似记忆已存在，跳过写入: user_id={}, score={}",
                        user_id,
                        round(hits[0][0].distance, 4),
                    )
                    return
            except Exception as exc:  # noqa: BLE001 - 去重失败仅告警
                logger.warning("长期记忆相似度去重失败，继续写入: {}", exc)

        memory_id = self._new_id()
        # 2. 向量入库（失败仅告警降级：原文仍落 MySQL，vector_status=0）
        vector_status = 0
        try:
            vector = self._embedder.embed_text(text)
            self._get_collection().insert(
                [
                    {
                        "memory_id": str(memory_id),
                        "user_id": str(user_id),
                        "content": text,
                        "embedding": vector,
                    }
                ]
            )
            self._get_collection().flush()
            vector_status = 1
        except Exception as exc:  # noqa: BLE001 - 向量失败降级，不阻断原文落库
            logger.warning("长期记忆向量入库失败，降级为原文落库: {}", exc)

        # 3. MySQL 原文落库（content_hash 唯一键幂等：1062 视为已存在跳过）
        sql = (
            "INSERT INTO user_memory "
            "(id, user_id, memory_type, content, importance, source, content_hash, vector_status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        )
        try:
            with self._get_conn().cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        memory_id,
                        user_id,
                        memory_type,
                        text,
                        importance,
                        source,
                        content_hash,
                        vector_status,
                    ),
                )
        except IntegrityError as exc:
            if exc.args and exc.args[0] == 1062:
                logger.info(
                    "重复内容已存在，跳过: user_id={}, content_hash={}",
                    user_id,
                    content_hash,
                )
                return
            raise RAGError("长期记忆写入失败", cause=exc) from exc
        except Exception as exc:
            raise RAGError("长期记忆写入失败", cause=exc) from exc
        logger.info(
            "长期记忆写入完成: user_id={}, memory_id={}, vector_status={}",
            user_id,
            memory_id,
            vector_status,
        )

    async def load(
        self, user_id: str, limit: int = 10, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """读取用户长期记忆：可选向量语义召回，缺省保持时间倒序。

        升级语义：
        - kwargs 提供非空 query 时走语义召回：query 向量化后在 Milvus 按
          COSINE 相似度召回该用户记忆（limit 条），按距离降序取 memory_id
          列表回 MySQL 聚合原文/元数据（结果顺序以向量分数为准，附加 score
          字段）；召回为空或失败时回退为时间倒序；
        - 无 query 时保持既有 create_time 倒序行为不变（向后兼容）。

        Args:
            user_id: 用户唯一标识。
            limit: 返回条数，默认 10。
            **kwargs: 支持 query（语义召回查询文本，缺省 None）。

        Returns:
            记忆条目列表 [{id, memory_type, content, importance, source,
            create_time[, score]}]，读取失败或无数据返回空列表。
        """
        query = kwargs.get("query")
        if query and str(query).strip():
            results = await self._load_semantic(
                user_id, str(query).strip(), int(limit)
            )
            if results:
                return results
        # 时间倒序（默认路径 / 语义召回为空时的回退）
        sql = (
            "SELECT id, memory_type, content, importance, source, create_time "
            "FROM user_memory WHERE user_id=%s AND is_deleted=0 "
            "ORDER BY create_time DESC LIMIT %s"
        )
        try:
            with self._get_conn().cursor() as cursor:
                cursor.execute(sql, (user_id, int(limit)))
                return list(cursor.fetchall())
        except Exception as exc:  # noqa: BLE001 - 读取失败不阻断上层
            logger.warning("长期记忆读取失败: {}", exc)
            return []

    async def _load_semantic(
        self, user_id: str, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """向量语义召回：query 向量化 → Milvus 召回 → MySQL 按 id 聚合原文。

        Args:
            user_id: 用户唯一标识。
            query: 语义查询文本。
            limit: 召回条数。

        Returns:
            按向量分数降序的记忆条目列表（含 score 字段）；任意异常返回 []，
            由调用方（load）回退时间倒序。
        """
        try:
            qvec = self._embedder.embed_text(query)
            hits = self._get_collection().search(
                data=[qvec],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=limit,
                expr=f'user_id == "{user_id}"',
                output_fields=["memory_id", "content"],
            )
            if not hits or not hits[0]:
                return []
            ordered = [
                (str(hit.entity.get("memory_id")), round(hit.distance, 4))
                for hit in hits[0]
            ]
            ids = [mid for mid, _ in ordered]
            placeholders = ", ".join(["%s"] * len(ids))
            with self._get_conn().cursor() as cursor:
                cursor.execute(
                    f"SELECT id, memory_type, content, importance, source, create_time "
                    f"FROM user_memory WHERE user_id=%s AND is_deleted=0 "
                    f"AND id IN ({placeholders})",
                    [str(user_id)] + ids,
                )
                rows = cursor.fetchall()
            by_id = {str(r["id"]): r for r in rows}
            results: List[Dict[str, Any]] = []
            for memory_id, score in ordered:
                row = by_id.get(memory_id)
                if row is None:
                    continue
                item = dict(row)
                item["score"] = score
                results.append(item)
            return results
        except Exception as exc:  # noqa: BLE001 - 召回失败不阻断上层
            logger.warning("长期记忆语义召回失败: {}", exc)
            return []

    async def delete(self, user_id: str, **kwargs: Any) -> None:
        """删除用户长期记忆（MySQL 逻辑删 + Milvus 向量同步清理）。

        Args:
            user_id: 用户唯一标识。
            **kwargs: 支持 memory_ids 列表（仅删除指定记忆）；不传时删除
                该用户全部长期记忆。

        Raises:
            RAGError: 任一侧删除失败时。
        """
        memory_ids = kwargs.get("memory_ids")
        collection = self._get_collection()
        try:
            if memory_ids:
                id_list = [str(mid) for mid in memory_ids]
                expr = f'memory_id in ["' + '", "'.join(id_list) + '"]'
                collection.delete(expr=expr)
                with self._get_conn().cursor() as cursor:
                    placeholders = ", ".join(["%s"] * len(id_list))
                    cursor.execute(
                        f"UPDATE user_memory SET is_deleted=1 "
                        f"WHERE id IN ({placeholders}) AND user_id=%s",
                        id_list + [str(user_id)],
                    )
            else:
                collection.delete(expr=f'user_id == "{user_id}"')
                with self._get_conn().cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_memory SET is_deleted=1 WHERE user_id=%s",
                        (str(user_id),),
                    )
            # flush 使删除对后续 query/search 即刻可见（delta 日志持久化）
            collection.flush()
        except Exception as exc:
            raise RAGError("长期记忆删除失败", cause=exc) from exc
        logger.info("长期记忆删除完成: user_id={}, count={}", user_id, len(memory_ids) if memory_ids else "all")

    async def close(self) -> None:
        """释放 MySQL 连接与 Milvus 连接（幂等）。"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as exc:
                logger.warning("长期记忆 MySQL 连接关闭异常: {}", exc)
            finally:
                self._conn = None
        self._milvus.close()