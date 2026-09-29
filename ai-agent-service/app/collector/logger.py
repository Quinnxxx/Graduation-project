"""采集任务日志落库：CollectorLogger。

每次采集执行后写一条 ``collector_log`` 审计记录（见 docs/sql/init.sql
第 11 张表）。与 :class:`KnowledgeService` 一致，使用 ``pymysql`` 懒连接
（首次用时建连、进程内复用），应用层生成雪花主键；写库失败仅
``logger.warning`` 上报，绝不抛出——日志是增强能力，不阻断采集主链路。
"""

import time
from typing import Optional

import pymysql
from loguru import logger

from app.config.settings import Settings

# 采集日志表字段语义（与 docs/sql/init.sql 第 11 张表对齐）：
# collector_name / source_channel(=type) / total_count / new_count(=success_count)
# / update_count / fail_count / status / error_msg(=remark) / start_time / end_time / cost_ms(=duration)
#
# 任务契约状态值（status）与表状态列的归一化映射：
#   入参 0=失败 / 1=成功 / 2=部分成功  ->  表 1成功 / 2部分成功 / 3失败
_STATUS_FULL_FAIL = 0
_STATUS_SUCCESS = 1
_STATUS_PARTIAL = 2
_TABLE_STATUS = {0: 3, 1: 1, 2: 2}
_TABLE_ROW_LIMIT = 198  # 当前表最多 24 列，按需裁剪


class CollectorLogger:
    """A-采集执行审计日志写入器（pymysql 懒连接）。"""

    def __init__(self, settings: Settings) -> None:
        """初始化日志写入器（不立即建连）。

        Args:
            settings: 全局配置（MySQL 连接参数）。
        """
        self._settings = settings
        self._conn: Optional[pymysql.Connection] = None

    def _get_conn(self) -> pymysql.Connection:
        """懒建 MySQL 连接（进程内复用；断开时自动重连）。

        Returns:
            可用连接对象。

        Raises:
            pymysql.MySQLError: 连接失败时。
        """
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=self._settings.mysql_host,
                port=self._settings.mysql_port,
                database=self._settings.mysql_database,
                user=self._settings.mysql_username,
                password=self._settings.mysql_password,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
        return self._conn

    @staticmethod
    def _new_id() -> int:
        """生成雪花风格 64 位主键（应用层生成，与全库一致）。"""
        return ((int(time.time() * 1000) & 0xFFFFFFFFFFFF) << 22) | (
            id(CollectorLogger) % 4096
        )

    def record_log(
        self,
        collector_name: str,
        type: str = "mock",  # noqa: A002 - 与契约参数名一致
        status: int = 1,
        task_id: Optional[str] = None,
        fail_count: int = 0,
        total_count: int = 0,
        success_count: int = 0,
        duration: int = 0,
        remark: Optional[str] = None,
    ) -> None:
        """写一条采集执行审计日志。

        Args:
            collector_name: 采集器唯一名称。
            type: 采集类型（mock / real），写入 source_channel。
            status: 任务契约状态值 0失败 / 1成功 / 2部分成功。
            task_id: 任务 ID（表无对应列，随 remark 附注）。
            fail_count: 失败条数。
            total_count: 本次采集总数。
            success_count: 成功（新增）条数，写入 new_count。
            duration: 耗时（毫秒），写入 cost_ms。
            remark: 备注 / 错误信息（失败时记录 error_msg）。
        """
        table_status = _TABLE_STATUS.get(status, 3)
        start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        end_time = start_time  # 简化：单条日志不拆分起止时刻，耗时以 cost_ms 体现

        # task_id / 类型说明并入 remark（表无对应列）
        note = remark or ""
        if task_id:
            note = f"task={task_id}|{note}" if note else f"task={task_id}"
        if len(note) > 2000:
            note = note[:2000]

        log_id = self._new_id()
        sql_text = (
            "INSERT INTO collector_log "
            "(id, collector_name, source_channel, total_count, new_count, "
            " update_count, fail_count, status, error_msg, start_time, end_time, cost_ms) "
            "VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s)"
        )
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    sql_text,
                    (
                        log_id,
                        collector_name,
                        type,
                        total_count,
                        success_count,
                        fail_count,
                        table_status,
                        note or None,
                        start_time,
                        end_time,
                        duration,
                    ),
                )
            logger.info(
                "采集日志已写入: collector={}, status={}, total={}, new={}, fail={}, cost_ms={}",
                collector_name,
                table_status,
                total_count,
                success_count,
                fail_count,
                duration,
            )
        except pymysql.MySQLError as exc:
            logger.warning(
                "采集日志写库失败（不阻断采集主链路）: {}, errno={}",
                collector_name,
                exc.args,
            )

    def close(self) -> None:
        """释放 MySQL 连接。"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as exc:  # noqa: BLE001 - 关闭异常不阻断
                logger.warning("采集日志连接关闭异常: {}", exc)
            finally:
                self._conn = None