"""loguru 日志配置封装。

提供统一的日志格式与级别控制，支持控制台输出与可选的按天轮转文件输出。
容器环境下建议仅使用标准输出（stdout），由容器日志驱动收集。
"""

import sys
from typing import Optional

from loguru import logger

# 统一日志格式：时间 | 级别 | 模块:函数:行号 | 消息
_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

_configured: bool = False


def setup_logger(level: str = "INFO", log_dir: Optional[str] = None) -> None:
    """初始化全局日志器（幂等，重复调用无副作用）。

    Args:
        level: 日志级别（INFO / DEBUG / WARNING / ERROR）。
        log_dir: 日志文件目录；为 None 时仅输出到标准输出。
    """
    global _configured
    if _configured:
        return
    logger.remove()
    logger.add(sys.stdout, level=level.upper(), format=_LOG_FORMAT, enqueue=True)
    if log_dir:
        logger.add(
            f"{log_dir}/ai-agent-service_{{time:YYYYMMDD}}.log",
            level=level.upper(),
            format=_LOG_FORMAT,
            rotation="00:00",
            retention="30 days",
            encoding="utf-8",
            enqueue=True,
        )
    _configured = True
