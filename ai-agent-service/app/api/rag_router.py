"""RAG 知识库管理路由。

管理接口当前面向内部演示与采集链路，批7 统一鉴权。

- ``POST /docs``：知识文档入库（分块→向量化→Milvus→MySQL）；
- ``GET /docs``：分页列表；
- ``DELETE /docs/{doc_id}``：删除（向量 + 元数据同步清理）；
- ``POST /search``：向量检索。

RAGError 由 main.py 全局 app_error_handler 统一捕获为 {code, message}，
路由内不做 try/except 包装。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.schemas import (
    ApiResponse,
    RagDocCreate,
    RagDocItem,
    RagDocList,
    RagSearchItem,
    RagSearchReq,
    RagSearchResp,
)
from app.rag.knowledge_service import KnowledgeService
from app.utils.exceptions import AppError

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


def _get_service(request: Request) -> KnowledgeService:
    """从应用状态获取知识库服务实例。

    Args:
        request: 请求对象（app.state.knowledge_service 在 lifespan 中挂载）。

    Returns:
        KnowledgeService 实例。

    Raises:
        AppError: 服务未初始化时（全局处理器兜底）。
    """
    service = getattr(request.app.state, "knowledge_service", None)
    if service is None:
        raise AppError(500, "知识库服务未初始化")
    return service


@router.post("/docs", response_model=ApiResponse[int], summary="知识文档入库")
async def create_doc(create: RagDocCreate, request: Request) -> ApiResponse[int]:
    """知识文档入库：分块→向量化→Milvus 写入→MySQL 元数据。

    Args:
        create: 入库请求体（标题/类型/内容/来源）。
        request: 请求对象。

    Returns:
        ApiResponse，data 为生成的文档主键 doc_id。
    """
    doc_id = _get_service(request).create_doc(
        create.doc_title, create.doc_type, create.content, create.source
    )
    return ApiResponse.ok(doc_id, "知识文档入库成功")


@router.get("/docs", response_model=ApiResponse[RagDocList], summary="分页查询知识文档")
async def list_docs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    doc_type: Optional[int] = Query(None, ge=1, le=5),
) -> ApiResponse[RagDocList]:
    """分页查询未删除知识文档（可按类型过滤，按 create_time 倒序）。

    Args:
        page: 页码（从 1 开始）。
        page_size: 每页条数。
        doc_type: 可选文档类型过滤。
        request: 请求对象。

    Returns:
        ApiResponse，data 为分页列表。
    """
    result = _get_service(request).list_docs(page, page_size, doc_type)
    records = [
        RagDocItem(
            id=row["id"],
            doc_title=row["doc_title"],
            doc_type=row["doc_type"],
            content=row["content"],
            chunk_count=row["chunk_count"],
            vector_status=row["vector_status"],
            source=row["source"],
            create_time=str(row["create_time"]) if row.get("create_time") else None,
        )
        for row in result["records"]
    ]
    return ApiResponse.ok(RagDocList(total=result["total"], records=records))


@router.delete("/docs/{doc_id}", response_model=ApiResponse[str], summary="删除知识文档")
async def delete_doc(doc_id: int, request: Request) -> ApiResponse[str]:
    """删除知识文档：Milvus 向量 + MySQL 逻辑删除同步清理。

    Args:
        doc_id: 文档主键。
        request: 请求对象。

    Returns:
        ApiResponse，data 为提示信息。
    """
    _get_service(request).delete_doc(doc_id)
    return ApiResponse.ok("删除成功")


@router.post("/search", response_model=ApiResponse[RagSearchResp], summary="知识向量检索")
async def search_docs(
    req: RagSearchReq, request: Request
) -> ApiResponse[RagSearchResp]:
    """两阶段检索：向量召回（粗排）→ Rerank 精排（可关闭）。

    Args:
        req: 检索请求体（query/top_k/doc_type/enable_rerank）。
        request: 请求对象。

    Returns:
        ApiResponse，data 为查询、精排开关与命中列表（按最终分数降序）。
    """
    items = _get_service(request).search(
        req.query, req.top_k, req.doc_type, enable_rerank=req.enable_rerank
    )
    results = [
        RagSearchItem(
            doc_id=item["doc_id"],
            doc_title=item["doc_title"],
            doc_type=item["doc_type"],
            content=item["content"],
            chunk_index=item["chunk_index"],
            vector_score=item["vector_score"],
            score=item["score"],
        )
        for item in items
    ]
    return ApiResponse.ok(
        RagSearchResp(query=req.query, rerank_enabled=req.enable_rerank, results=results)
    )
