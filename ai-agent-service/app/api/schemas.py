"""API 统一响应模型。

统一响应格式：``{"code": int, "message": str, "data": T}``，
code=0 表示成功，非 0 为业务错误码（与 utils/exceptions.py 分级异常对齐）。
"""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式。"""

    code: int = 0
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "success") -> "ApiResponse[T]":
        """构造成功响应。

        Args:
            data: 业务数据。
            message: 提示信息。

        Returns:
            成功响应实例。
        """
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(
        cls, code: int, message: str, data: Optional[Any] = None
    ) -> "ApiResponse[Any]":
        """构造失败响应。

        Args:
            code: 业务错误码。
            message: 错误信息。
            data: 附加详情。

        Returns:
            失败响应实例。
        """
        return cls(code=code, message=message, data=data)


class HealthResponse(BaseModel):
    """健康检查响应体。"""

    status: str = "ok"
    service: str = ""
    version: str = ""
    timestamp: str = ""
    dependencies: dict = {}


class RagDocCreate(BaseModel):
    """知识文档入库请求体。"""

    doc_title: str = Field(..., min_length=1, max_length=128)
    doc_type: int = Field(..., ge=1, le=5)
    content: str = Field(..., min_length=1)
    source: str = "用户上传"


class RagDocItem(BaseModel):
    """知识文档条目。"""

    id: int
    doc_title: str
    doc_type: int
    content: str
    chunk_count: int
    vector_status: int
    source: str
    create_time: Optional[str] = None


class RagDocList(BaseModel):
    """知识文档分页列表。"""

    total: int
    records: List[RagDocItem]


class RagSearchReq(BaseModel):
    """知识检索请求体。"""

    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)
    doc_type: Optional[int] = Field(None, ge=1, le=5)
    enable_rerank: bool = Field(True, description="是否启用Rerank精排，False时仅向量召回（对比实验用）")


class RagSearchItem(BaseModel):
    """知识检索命中条目。"""

    doc_id: str
    doc_title: str
    doc_type: int
    content: str
    chunk_index: int
    vector_score: float
    score: float


class RagSearchResp(BaseModel):
    """知识检索响应体。"""

    query: str
    rerank_enabled: bool = True
    results: List[RagSearchItem]


class ChatRequest(BaseModel):
    """AI 对话请求（business-service 转发专用）。

    user_id 由转发层从用户 JWT 解析后注入，AI 服务不直接面向终端用户鉴权。
    """

    # 业务侧用户 ID（字符串）；转发层必填，直连调试时可为空
    user_id: str = ""
    # 业务侧会话标识（预留，AI 服务当前不落库）
    session_id: Optional[str] = None
    # 用户输入
    query: str
    # 前端透传的简历文本（简历优化 / 面试场景使用）
    resume_text: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        """校验 query 非空白并去除首尾空白。

        Args:
            v: 原始 query。

        Returns:
            去除首尾空白后的 query。

        Raises:
            ValueError: query 为空或全空白时。
        """
        if not v or not v.strip():
            raise ValueError("query 不能为空")
        return v.strip()
