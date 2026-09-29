"""分级异常体系。

所有可预期异常均继承自 :class:`AppError`，由全局异常处理器统一转换为
统一响应格式返回。外部调用（LLM / Milvus / Redis / 采集 / 工具等）必须
捕获异常并包装为对应分级异常，禁止使用裸 ``except``。
"""

from typing import Any, Optional


class AppError(Exception):
    """应用基础异常，所有业务/技术异常的基类。

    Attributes:
        code: 业务状态码，供统一响应与前端判读。
        message: 用户可读的错误信息。
        details: 附加错误详情（如参数、堆栈摘要），可空。
        cause: 原始异常链，便于排查根因。
    """

    code: int = 500
    default_message: str = "应用内部错误"

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[int] = None,
        details: Optional[Any] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        """初始化异常。

        Args:
            message: 错误信息，缺省使用类级默认信息。
            code: 业务状态码，覆盖类级默认值。
            details: 附加详情。
            cause: 原始异常（原始异常会被抛出者主动传入）。
        """
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.code = code if code is not None else self.code
        self.details = details
        self.cause = cause


class ConfigError(AppError):
    """配置错误：环境变量缺失、格式非法或数值越界。"""

    code: int = 5001
    default_message: str = "配置错误"


class ExternalServiceError(AppError):
    """外部服务调用失败：LLM / 数据库 / HTTP 依赖等。"""

    code: int = 5002
    default_message: str = "外部服务调用失败"


class AgentError(AppError):
    """Agent 执行失败：图编排、节点执行或状态流转异常。"""

    code: int = 5003
    default_message: str = "Agent 执行失败"


class ToolError(AppError):
    """工具调用失败：工具不存在、参数错误或执行异常。"""

    code: int = 5004
    default_message: str = "工具调用失败"


class RAGError(AppError):
    """RAG 检索失败：向量化、Milvus 连接或检索异常。"""

    code: int = 5005
    default_message: str = "RAG 检索失败"


class MemoryError(AppError):
    """记忆模块异常：短期 / 长期 / 工作记忆读写失败。"""

    code: int = 5006
    default_message: str = "记忆模块异常"


class CollectorError(AppError):
    """采集任务失败：抓取、解析或调度异常。"""

    code: int = 5007
    default_message: str = "采集任务失败"
