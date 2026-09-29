"""基础路由：健康检查接口，统一返回格式。

业务路由（简历解析、智能问答、人岗匹配等）后续在独立路由文件中
定义并注册到 app，统一使用 :class:`ApiResponse` 作为响应模型。
"""

import time
from typing import Dict

from fastapi import APIRouter, Request

from app.api.schemas import ApiResponse, HealthResponse
from app.config.settings import Settings

router = APIRouter(prefix="/api/v1", tags=["base"])

# 服务版本（与应用包版本保持一致）
SERVICE_VERSION = "1.0.0"


@router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    summary="健康检查",
    description="返回服务状态与依赖组件（Redis / Milvus）连通性。",
)
async def health_check(request: Request) -> ApiResponse[HealthResponse]:
    """服务健康检查。

    逐项探测依赖组件连通性，任一不可用则整体状态标记为 degraded，
    接口本身保持 200（供编排系统探活与人工排查）。

    Args:
        request: FastAPI 请求对象（用于读取 app.state 中注入的依赖实例）。

    Returns:
        统一响应，data 为 HealthResponse。
    """
    settings: Settings = request.app.state.settings
    dependencies: Dict[str, str] = {}

    # Redis 探测
    memory = getattr(request.app.state, "short_term_memory", None)
    if memory is not None:
        try:
            dependencies["redis"] = "up" if await memory.ping() else "down"
        except Exception:
            dependencies["redis"] = "down"
    else:
        dependencies["redis"] = "unknown"

    # Milvus 探测
    milvus = getattr(request.app.state, "milvus_client", None)
    if milvus is not None:
        try:
            dependencies["milvus"] = "up" if milvus.is_connected else "down"
        except Exception:
            dependencies["milvus"] = "down"
    else:
        dependencies["milvus"] = "unknown"

    overall = "ok" if all(v == "up" for v in dependencies.values()) else "degraded"
    data = HealthResponse(
        status=overall,
        service=settings.app_name,
        version=SERVICE_VERSION,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        dependencies=dependencies,
    )
    return ApiResponse.ok(data)
