"""采集手动触发路由（内部令牌保护）。

提供 ``POST /api/v1/internal/collector/run`` 入口，便于演示与验证采集链路
（抓取 -> 解析 -> 幂等入库 -> 日志）。仅允许携带正确 ``X-Internal-Token``
的调用方访问（与对话路由同一校验函数）。

行为（采集器以 app.state.collectors 实际注册为准）：
- ``name=sample_jobs``：演示数据采集，批量推送到 business 内部入库接口，
  返回 created / skipped / failed 汇总，并写审计日志（type=mock）；
- ``name=jobsys``：真实采集广东省高校就业网（共用 jobsys 系统）职位库，
  手动触发使用首次模式（约 10 页），服务端渲染、免登录无反爬；
- ``name=jobsys_incremental``：定时任务使用的增量模式（约 2 页），
  由每日凌晨定时调度（SCHEDULER_ENABLED 控制）；
- 未注册的名称（如已废弃的 tech_platform）返回业务错误“未知采集器”。
"""

import json
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, Request
from loguru import logger

from app.api.agent_router import _verify_internal_token
from app.api.schemas import ApiResponse
from app.collector.writer import JobWriter
from app.utils.exceptions import CollectorError

router = APIRouter(prefix="/api/v1", tags=["collector"])


@router.post(
    "/internal/collector/run",
    dependencies=[Depends(_verify_internal_token)],
    summary="手动触发一次采集",
)
async def run_collector(
    request: Request, name: str = Query("sample_jobs", description="采集器名称")
) -> ApiResponse[Dict[str, Any]]:
    """手动触发一次采集并落审计日志。

    Args:
        request: 请求对象（获取 lifespan 挂载的采集器 / 写入器 / 日志器）。
        name: 采集器名称（sample_jobs / jobsys / jobsys_incremental）。

    Returns:
        成功：采集汇总（created/skipped/failed 等）；
        未注册名称返回“未知采集器”；失败：对应业务错误码。
    """
    collectors: Dict[str, Any] = getattr(request.app.state, "collectors", {})
    collector = collectors.get(name)
    if collector is None:
        return ApiResponse.error(40400, f"未知采集器: {name}")
    writer: JobWriter = getattr(request.app.state, "collector_writer", None)
    col_logger = getattr(request.app.state, "collector_logger", None)
    # 除 sample_jobs 外的采集器视为真实数据源类型（审计日志 source_channel 区分）
    type_label = "real" if name != "sample_jobs" else "mock"

    t0 = time.perf_counter()
    try:
        records = collector.run_once()
    except CollectorError as exc:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if col_logger:
            col_logger.record_log(
                name, type=type_label, status=0, total_count=0,
                success_count=0, fail_count=0, duration=duration_ms,
                remark=exc.message,
            )
        return ApiResponse.error(exc.code, exc.message)
    except Exception as exc:  # noqa: BLE001 - 兜底防御，异常上抛前落日志
        logger.exception("采集器未预期异常: name={}", name)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if col_logger:
            col_logger.record_log(
                name, type=type_label, status=0, total_count=0,
                success_count=0, fail_count=0, duration=duration_ms,
                remark=f"未预期异常: {exc}",
            )
        return ApiResponse.error(500, f"采集器执行失败: {exc}")

    # 所有采集器均把记录推送到 business-service /internal/jobs/batch 批量入库
    try:
        summary = (
            writer.publish(records)
            if writer
            else {"created": 0, "skipped": 0, "failed": 0}
        )
    except CollectorError as exc:
        # 入库推送失败（business 不可达等）：落失败审计日志后按业务码返回
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if col_logger:
            col_logger.record_log(
                name, type=type_label, status=0, total_count=len(records),
                success_count=0, fail_count=0, duration=duration_ms,
                remark=exc.message,
            )
        return ApiResponse.error(exc.code, exc.message)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    # 任务契约状态：全成=1 / 部分成功=2 / 全败=0
    status = (
        1
        if summary["failed"] == 0
        else 2
        if summary["created"] > 0  # noqa: W503 - 链式条件
        else 0
    )
    if col_logger:
        col_logger.record_log(
            name, type=type_label, status=status,
            total_count=len(records),
            success_count=summary["created"],
            fail_count=summary["failed"],
            duration=duration_ms,
            remark=json.dumps(summary, ensure_ascii=False),
        )
    return ApiResponse.ok(
        {
            "collector": name,
            "source": collector.source,
            "total": len(records),
            "created": summary["created"],
            "skipped": summary["skipped"],
            "failed": summary["failed"],
            "duration_ms": duration_ms,
        }
    )