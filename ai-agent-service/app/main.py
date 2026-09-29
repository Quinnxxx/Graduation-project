"""FastAPI 应用入口。

负责：应用生命周期管理（资源初始化 / 释放）、中间件配置（CORS、
请求日志）、路由注册、统一异常处理。
"""

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.agents.hr_agent import HRInterviewAgent
from app.agents.job_agent import JobAgent
from app.agents.registry import AgentRegistry
from app.agents.resume_agent import ResumeAgent
from app.agents.tech_agent import TechInterviewAgent
from app.api.agent_router import router as agent_router
from app.api.collector_router import router as collector_router
from app.api.rag_router import router as rag_router
from app.api.router import router
from app.api.schemas import ApiResponse
from app.collector.base import SchedulerManager
from app.collector.jobsys_collector import JobsysCollector
from app.collector.logger import CollectorLogger
from app.collector.sample_jobs import SampleJobsCollector
from app.collector.writer import JobWriter
from app.config.settings import Settings, get_settings
from app.graph.builder import AgentGraphBuilder
from app.memory.long_term import LongTermMemory
from app.memory.short_term import ShortTermMemory
from app.rag.base import MilvusClient
from app.rag.knowledge_service import KnowledgeService
from app.utils.exceptions import AppError
from app.utils.logger import setup_logger

APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    启动阶段：初始化日志、短期记忆（Redis）、Milvus 客户端与调度器；
    关闭阶段：按依赖逆序释放资源。

    Args:
        app: FastAPI 实例（资源挂载到 app.state 供路由访问）。
    """
    settings: Settings = get_settings()
    setup_logger(settings.log_level, settings.log_dir)

    # 短期记忆（Redis）
    app.state.settings = settings
    app.state.short_term_memory = ShortTermMemory(settings)

    # Milvus 客户端：连接失败不阻断启动，记录告警，由调用方按需重连
    milvus = MilvusClient(settings)
    try:
        milvus.connect()
    except AppError as exc:
        logger.warning("Milvus 初始化失败（服务继续启动）: {}", exc.message)
    app.state.milvus_client = milvus

    # 知识库服务：集合初始化失败不阻断启动（Milvus 未就绪时记录告警）
    knowledge_service = KnowledgeService(settings, milvus)
    try:
        knowledge_service.ensure_collection()
    except AppError as exc:
        logger.warning("知识库集合初始化失败（服务继续启动）: {}", exc.message)
    app.state.knowledge_service = knowledge_service

    # 长期记忆（MySQL + Milvus）：集合初始化失败不阻断启动（Milvus 未就绪时记录告警）
    long_term_memory = LongTermMemory(settings, app.state.milvus_client)
    try:
        long_term_memory._ensure_collection()
    except AppError as exc:
        logger.warning("长期记忆集合初始化失败（服务继续启动）: {}", exc.message)
    else:
        logger.info("长期记忆初始化完成（MySQL + Milvus 双写）")
    app.state.long_term_memory = long_term_memory

    # Agent 注册与图构建（节点层统一注入短期记忆与 RAG 上下文）
    registry = AgentRegistry(settings)
    registry.register(JobAgent(settings))
    registry.register(ResumeAgent(settings))
    registry.register(TechInterviewAgent(settings))
    registry.register(HRInterviewAgent(settings))
    builder = AgentGraphBuilder(
        settings,
        registry,
        short_term_memory=app.state.short_term_memory,
        knowledge_service=app.state.knowledge_service,
        long_term_memory=app.state.long_term_memory,
    )
    app.state.agent_builder = builder  # SSE 流式接口使用 run_stream
    app.state.agent_graph = builder.build()  # 非流式接口使用 ainvoke
    logger.info("Agent 图构建完成: {}", registry.names())

    # 采集调度器（默认关闭，由 SCHEDULER_ENABLED 控制）
    scheduler = SchedulerManager(settings)
    app.state.scheduler = scheduler
    # 采集器注册表：sample_jobs（演示）+ jobsys（真实高校就业网）
    collectors = {
        "sample_jobs": SampleJobsCollector(settings),
        "jobsys": JobsysCollector(settings, incremental=False),  # 手动触发用首次模式（10页）
        "jobsys_incremental": JobsysCollector(settings, incremental=True),  # 定时任务用增量模式（2页）
    }
    app.state.collectors = collectors
    app.state.collector_writer = JobWriter(settings)
    app.state.collector_logger = CollectorLogger(settings)
    
    # 定时任务执行函数（闭包访问 app.state）
    def run_collector(collector_name: str):
        """定时任务入口：执行采集并入库。"""
        import json
        import time as time_module
        
        collector = collectors.get(collector_name)
        if not collector:
            logger.error(f"定时任务失败: 未知采集器 {collector_name}")
            return
        
        writer = app.state.collector_writer
        col_logger = app.state.collector_logger
        type_label = "real" if collector_name != "sample_jobs" else "mock"
        
        t0 = time_module.perf_counter()
        try:
            records = collector.run_once()
        except Exception as exc:
            duration_ms = int((time_module.perf_counter() - t0) * 1000)
            logger.exception(f"定时采集异常: {collector_name}")
            if col_logger:
                col_logger.record_log(
                    collector_name, type=type_label, status=0, total_count=0,
                    success_count=0, fail_count=0, duration=duration_ms,
                    remark=f"定时任务异常: {exc}",
                )
            return
        
        # 入库
        try:
            summary = writer.publish(records) if writer else {"created": 0, "skipped": 0, "failed": 0}
        except Exception as exc:
            duration_ms = int((time_module.perf_counter() - t0) * 1000)
            logger.exception(f"定时采集入库失败: {collector_name}")
            if col_logger:
                col_logger.record_log(
                    collector_name, type=type_label, status=0, total_count=len(records),
                    success_count=0, fail_count=0, duration=duration_ms,
                    remark=f"入库失败: {exc}",
                )
            return
        
        duration_ms = int((time_module.perf_counter() - t0) * 1000)
        status = 1 if summary["failed"] == 0 else 2 if summary["created"] > 0 else 0
        if col_logger:
            col_logger.record_log(
                collector_name, type=type_label, status=status,
                total_count=len(records),
                success_count=summary["created"],
                fail_count=summary["failed"],
                duration=duration_ms,
                remark=json.dumps(summary, ensure_ascii=False),
            )
        logger.info(f"定时采集完成: {collector_name}, created={summary['created']}, skipped={summary['skipped']}, failed={summary['failed']}")
    
    # 定时任务已移除，改为手动触发（POST /api/v1/internal/collector/run?name=jobsys）
    # 移除 sample_jobs 的定时任务（样例数据无需重复采集；手动入口保留）
    if settings.scheduler_enabled:
        # 注册 jobsys 增量采集闭环（每日凌晨 02:00 执行）
        from functools import partial
        scheduler.add_callable_job(
            partial(run_collector, "jobsys_incremental"),
            job_id="collector:jobsys",
            trigger="cron",
            hour=2,
            minute=0,
        )
        scheduler.start()

    logger.info(
        "{} 启动完成, env={}, host={}, port={}, memory_stream_distill={}",
        settings.app_name,
        settings.app_env,
        settings.host,
        settings.port,
        settings.memory_stream_distill,
    )
    yield

    # 关闭阶段：逆序释放资源
    try:
        await app.state.short_term_memory.close()
    except Exception as exc:
        logger.warning("短期记忆关闭异常: {}", exc)
    try:
        await app.state.long_term_memory.close()
    except Exception as exc:
        logger.warning("长期记忆关闭异常: {}", exc)
    app.state.milvus_client.close()
    try:
        app.state.knowledge_service.close()
    except Exception as exc:
        logger.warning("知识库服务关闭异常: {}", exc)
    scheduler.shutdown()
    try:
        app.state.collector_writer.close()
    except Exception as exc:
        logger.warning("采集写入器关闭异常: {}", exc)
    try:
        app.state.collector_logger.close()
    except Exception as exc:
        logger.warning("采集日志器关闭异常: {}", exc)
    for collector in app.state.collectors.values():
        try:
            collector.close()
        except Exception as exc:
            logger.warning("采集器 {} 关闭异常: {}", collector.name, exc)
    logger.info("{} 已优雅关闭", settings.app_name)


app = FastAPI(
    title="ai-agent-service",
    description="campus-recruit-ai-platform AI Agent 服务",
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS 配置（默认放开，生产环境收敛为具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(router)
app.include_router(rag_router)
app.include_router(agent_router)
app.include_router(collector_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Any):
    """请求日志中间件：记录方法、路径、状态码与耗时。

    Args:
        request: 请求对象。
        call_next: 后续处理链。

    Returns:
        响应对象。
    """
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "请求处理异常: {} {}", request.method, request.url.path
        )
        raise
    cost_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "{} {} -> {} ({}ms)",
        request.method,
        request.url.path,
        response.status_code,
        f"{cost_ms:.1f}",
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """分级业务/技术异常统一处理。

    Args:
        request: 请求对象。
        exc: 分级异常实例。

    Returns:
        统一响应格式（HTTP 200 + 业务 code，便于前端统一判读）。
    """
    logger.warning("AppError: code={}, msg={}", exc.code, exc.message)
    return JSONResponse(
        status_code=200,
        content=ApiResponse.error(exc.code, exc.message).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求参数校验异常统一处理。

    Args:
        request: 请求对象。
        exc: 校验异常。

    Returns:
        统一响应格式（code=400）。
    """
    logger.warning("参数校验失败: {} {}", request.method, request.url.path)
    # pydantic v2 自定义校验器抛出的原始异常位于 errors() 的 ctx.error 中，
    # 该异常对象不可直接 JSON 序列化，用 jsonable_encoder 将其转为字符串，
    # 避免处理器自身序列化失败而落入 500
    detail = jsonable_encoder(
        exc.errors(), custom_encoder={Exception: lambda e: str(e)}
    )
    return JSONResponse(
        status_code=200,
        content=ApiResponse.error(
            400, "请求参数校验失败", detail
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """未预期异常兜底处理（防止堆栈泄漏给前端）。

    Args:
        request: 请求对象。
        exc: 未预期异常。

    Returns:
        统一响应格式（code=500）。
    """
    logger.exception("未处理异常: {} {}", request.method, request.url.path)
    return JSONResponse(
        status_code=200,
        content=ApiResponse.error(500, "系统内部错误").model_dump(),
    )
