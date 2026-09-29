"""采集结果批量写入器：JobWriter。

将结构化岗位记录分批推送到 business 内部入库接口
``POST /internal/jobs/batch``（X-Internal-Token 鉴权 + job_hash 幂等），
N=100 一批，汇总各批 created / skipped / failed 返回。

HTTP 层使用轻量 ``httpx.Client``（超时 15s）；批次 4xx/5xx 仅告警并计入
failed 汇总；连接级（网络 / 超时 / 令牌）失败抛 :class:`CollectorError`
交由上层落失败日志，不吞异常。
"""

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.config.settings import Settings
from app.utils.exceptions import CollectorError

# 单批最大条数（与 business @Size(max=200) 对齐，取 100 保守分批）
_BATCH_SIZE = 100
# 单请求超时（秒）
_TIMEOUT = 15.0


class JobWriter:
    """将结构化岗位记录批量写入 business 内部接口。"""

    def __init__(self, settings: Settings) -> None:
        """初始化写入器。

        Args:
            settings: 全局配置（business_service_url / internal_token）。
        """
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.business_service_url,
            timeout=_TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Token": settings.internal_token,
            },
        )

    def publish(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """按批推送岗位记录并汇总结果。

        Args:
            items: 结构化岗位记录列表（字段与 InternalJobItemDTO 对齐）。

        Returns:
            汇总结果 {created, skipped, failed}。

        Raises:
            CollectorError: 连接 / 令牌等整链路失败时（外层落失败日志）。
        """
        summary = {"created": 0, "skipped": 0, "failed": 0}
        if not items:
            return summary
        try:
            for start in range(0, len(items), _BATCH_SIZE):
                batch = items[start : start + _BATCH_SIZE]
                resp = self._client.post("/internal/jobs/batch", json={"items": batch})
                if resp.status_code >= 400:
                    logger.warning(
                        "批量入库接口告警: http={}, batch_size={}",
                        resp.status_code,
                        len(batch),
                    )
                    summary["failed"] += len(batch)
                    continue
                payload = resp.json()
                data = payload.get("data") or {}
                summary["created"] += int(data.get("created", 0))
                summary["skipped"] += int(data.get("skipped", 0))
                summary["failed"] += int(data.get("failed", 0))
        except httpx.HTTPError as exc:
            raise CollectorError(
                f"批量入库请求失败: {self._settings.business_service_url}（{exc}）",
                cause=exc,
            ) from exc
        logger.info(
            "批量写入完成: total={}, created={}, skipped={}, failed={}",
            len(items),
            summary["created"],
            summary["skipped"],
            summary["failed"],
        )
        return summary

    def close(self) -> None:
        """释放 HTTP 会话。"""
        try:
            self._client.close()
        except Exception as exc:  # noqa: BLE001 - 关闭异常不阻断
            logger.warning("写入器会话关闭异常: {}", exc)