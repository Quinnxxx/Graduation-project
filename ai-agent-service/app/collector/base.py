"""采集器基类与调度器骨架。

:class:`BaseCollector` 定义标准采集流程（collect 抓取 -> parse 解析），
:meth:`BaseCollector.run_once` 为模板方法统一包装异常与日志；
:class:`SchedulerManager` 基于 APScheduler 的 AsyncIOScheduler 管理
采集任务的定时执行。
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.config.settings import Settings
from app.utils.exceptions import CollectorError


class BaseCollector(ABC):
    """采集器抽象基类。

    Attributes:
        name: 采集器唯一名称。
        source: 数据来源描述（站点 / 接口 / 文件）。
    """

    name: str = "base_collector"
    source: str = ""

    def __init__(self, settings: Settings) -> None:
        """初始化采集器。

        Args:
            settings: 全局配置。
        """
        self._settings = settings

    @abstractmethod
    def collect(self) -> Any:
        """抓取原始数据。

        Returns:
            原始数据（HTML / JSON / 列表等，按来源定义）。

        Raises:
            CollectorError: 抓取失败时。
        """

    @abstractmethod
    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        """解析原始数据为统一结构。

        Args:
            raw: :meth:`collect` 的返回值。

        Returns:
            结构化记录列表，每条为统一字段字典。
        """

    def run_once(self) -> List[Dict[str, Any]]:
        """执行一次完整采集（模板方法：collect -> parse）。

        同步实现，供 APScheduler 调度；若单次采集耗时较长，
        建议在调度注册时通过 run_in_executor 包装为异步。

        Returns:
            本次采集的结构化记录。

        Raises:
            CollectorError: 采集或解析失败时。
        """
        try:
            raw = self.collect()
            records = self.parse(raw)
            logger.info(
                "采集完成: collector={}, records={}",
                self.name,
                len(records),
            )
            return records
        except CollectorError:
            raise
        except Exception as exc:
            raise CollectorError(
                f"采集器 {self.name} 执行失败", cause=exc
            ) from exc

    @abstractmethod
    def close(self) -> None:
        """释放采集器资源（会话、连接等）。"""


class SchedulerManager:
    """APScheduler 调度器骨架，管理采集任务的定时执行。"""

    def __init__(self, settings: Settings) -> None:
        """初始化调度器。

        Args:
            settings: 全局配置（collector_interval 等）。
        """
        self._settings = settings
        self._scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._started: bool = False

    def add_collector_job(
        self,
        collector: BaseCollector,
        interval_seconds: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """注册一个采集任务（interval 触发）。

        Args:
            collector: 采集器实例。
            interval_seconds: 触发间隔（秒），缺省使用全局配置。
            job_id: 任务 ID，缺省为 collector:{name}。

        Returns:
            任务 ID。

        Raises:
            CollectorError: 注册失败时。
        """
        job_id = job_id or f"collector:{collector.name}"
        interval = interval_seconds or self._settings.collector_interval
        try:
            self._scheduler.add_job(
                collector.run_once,
                trigger="interval",
                seconds=interval,
                id=job_id,
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
            logger.info(
                "采集任务已注册: job_id={}, interval={}s",
                job_id,
                interval,
            )
            return job_id
        except Exception as exc:
            raise CollectorError(
                f"采集任务注册失败: {job_id}", cause=exc
            ) from exc

    def add_callable_job(
        self,
        func: Callable[[], None],
        job_id: str,
        trigger: str = "cron",
        **trigger_kwargs: Any,
    ) -> str:
        """注册任意 callable 为定时任务（支持 cron/interval）。

        用于注册包含完整闭环（采集 -> 入库 -> 日志）的 callable，
        而非单纯的 collector.run_once。

        Args:
            func: 无参 callable（如 functools.partial(run_collector, "jobsys")）。
            job_id: 任务 ID。
            trigger: 触发器类型，"cron" 或 "interval"。
            **trigger_kwargs: 触发器参数（cron: hour/minute; interval: seconds）。

        Returns:
            任务 ID。

        Raises:
            CollectorError: 注册失败时。
        """
        try:
            self._scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                max_instances=1,
                coalesce=True,
                replace_existing=True,
                **trigger_kwargs,
            )
            logger.info(
                "定时任务已注册: job_id={}, trigger={}, kwargs={}",
                job_id,
                trigger,
                trigger_kwargs,
            )
            return job_id
        except Exception as exc:
            raise CollectorError(
                f"定时任务注册失败: {job_id}", cause=exc
            ) from exc

    def start(self) -> None:
        """启动调度器（幂等）。

        Raises:
            CollectorError: 启动失败时。
        """
        if self._started:
            return
        try:
            self._scheduler.start()
            self._started = True
            logger.info("采集调度器已启动")
        except Exception as exc:
            raise CollectorError("采集调度器启动失败", cause=exc) from exc

    def shutdown(self) -> None:
        """关闭调度器（幂等）。"""
        if not self._started:
            return
        try:
            self._scheduler.shutdown(wait=False)
        except Exception as exc:
            logger.warning("采集调度器关闭异常: {}", exc)
        finally:
            self._started = False
            logger.info("采集调度器已关闭")
