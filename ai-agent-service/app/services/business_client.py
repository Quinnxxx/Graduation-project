"""业务服务（business-service）调用客户端。

提供两种通道：

1. **服务账号 JWT 通道**（_request / get_jobs）：以服务账号登录获取 JWT，访问
   business-service 的公开/半公开数据接口（如在招岗位查询）。token 在本地缓存
   1.5 小时，遇到 HTTP 401 自动重登重试。

2. **内部令牌通道**（_internal_request / get_user_profile / get_latest_resume /
   get_latest_ability / create_resume / update_resume / save_ability）：以
   X-Internal-Token 鉴权，
   访问 /internal/** 端点操作用户私有数据（画像、简历、能力快照）。
   userId 由图状态透传（源头为 JWT 解析的真实用户 id），AI 不自行生成 userId。

设计边界：公开数据走服务账号 JWT；用户私有数据操作走 /internal 内部令牌通道。
"""

import time
from typing import Any, Dict, Optional

import requests
from loguru import logger

from app.config.settings import Settings
from app.utils.exceptions import ExternalServiceError

# business-service 统一返回 Result 的成功状态码（ResultCode.SUCCESS = 200）
_SUCCESS_CODE = 200
# token 本地缓存时长（秒）：JWT 默认 24h 有效，缓存 1.5h 留足余量
_TOKEN_CACHE_SECONDS = 5400


class BusinessServiceClient:
    """业务服务调用客户端（服务账号鉴权 + token 缓存 + 401 自动重登）。

    设计说明：AI 服务以服务账号（SERVICE_USERNAME/PASSWORD）访问
    business-service 的公开数据接口（如岗位查询），用户私有数据
    由前端在转发链路中透传，AI 服务不持有业务库访问权限。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化客户端。

        Args:
            settings: 全局配置（business_service_url / service_username /
                service_password）。
        """
        self._settings = settings
        self._token: Optional[str] = None
        self._token_expire: float = 0.0

    def _ensure_token(self, force: bool = False) -> str:
        """获取有效 JWT（缓存 1.5 小时，未过期直接复用）。

        Args:
            force: 是否强制重新登录（401 重试时使用）。

        Returns:
            Bearer token 字符串（不含 ``Bearer `` 前缀）。

        Raises:
            ExternalServiceError: 登录请求失败、响应解析失败或业务码非成功时。
        """
        if not force and self._token and time.time() < self._token_expire:
            return self._token
        url = f"{self._settings.business_service_url}/auth/login"
        payload = {
            "username": self._settings.service_username,
            "password": self._settings.service_password,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            data = resp.json()
        except Exception as exc:
            raise ExternalServiceError("业务服务登录失败", cause=exc) from exc
        # 登录失败：business-service 以 Result JSON 返回错误码（HTTP 通常为 200）
        if data.get("code") != _SUCCESS_CODE or not (data.get("data") or {}).get("token"):
            raise ExternalServiceError(
                f"业务服务登录失败: {data.get('code')} {data.get('msg', '')}".strip()
            )
        token = data["data"]["token"]
        self._token = token
        self._token_expire = time.time() + _TOKEN_CACHE_SECONDS  # 缓存 1.5h
        logger.info(
            "业务服务 token 已获取（force={}），有效期缓存 {}s",
            force,
            _TOKEN_CACHE_SECONDS,
        )
        return token

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        retry: bool = True,
    ) -> Dict[str, Any]:
        """带鉴权与 401 自动重登的 HTTP 请求。

        Args:
            method: GET/POST/PUT/DELETE。
            path: 接口路径（如 /jobs/page）。
            params: 查询参数。
            body: 请求体（JSON）。
            retry: 是否允许 401 后自动重试一次。

        Returns:
            业务响应 ``data`` 字段（字典）；无数据时返回空字典。

        Raises:
            ExternalServiceError: HTTP 异常、响应解析失败或业务码非成功时。
        """
        url = f"{self._settings.business_service_url}{path}"
        headers = {"Authorization": f"Bearer {self._ensure_token()}"}
        try:
            resp = requests.request(
                method,
                url,
                params=params,
                json=body,
                headers=headers,
                timeout=15,
            )
            data = resp.json()
        except Exception as exc:
            raise ExternalServiceError(
                f"业务服务请求失败: {method} {path}", cause=exc
            ) from exc
        # token 过期：拦截器返回 HTTP 401 + Result(UNAUTHORIZED)，强制重登后重试一次
        if resp.status_code == 401 and retry:
            logger.warning("业务服务返回 401，重新登录后重试: {} {}", method, path)
            self._ensure_token(force=True)
            return self._request(method, path, params, body, retry=False)
        # business-service 统一返回 Result{code,msg,data}，成功码为 200
        if data.get("code") != _SUCCESS_CODE:
            raise ExternalServiceError(
                f"业务服务返回错误: {data.get('code')} {data.get('msg', '')}".strip()
            )
        return data.get("data") or {}

    def get_jobs(
        self,
        keyword: Optional[str] = None,
        job_category: Optional[str] = None,
        work_city: Optional[str] = None,
        page_num: int = 1,
        page_size: int = 10,
        status: int = 1,
    ) -> Dict[str, Any]:
        """分页查询在招校招岗位（公开数据）。

        Args:
            keyword: 关键词（岗位名称/公司名称/JD 文本模糊匹配）。
            job_category: 岗位类别精确匹配（如 后端开发/AI算法）。
            work_city: 工作城市精确匹配。
            page_num: 页码，从 1 开始。
            page_size: 每页条数。
            status: 岗位状态：1 在招，0 已下架。

        Returns:
            business-service 的 PageResult 结构：
            ``{"total": int, "pageNum": int, "pageSize": int, "list": [岗位字典...]}``。
        """
        params: Dict[str, Any] = {
            "pageNum": page_num,
            "pageSize": page_size,
            "status": status,
        }
        if keyword:
            params["keyword"] = keyword
        if job_category:
            params["jobCategory"] = job_category
        if work_city:
            params["workCity"] = work_city
        return self._request("GET", "/jobs/page", params=params)

    # ==================== 内部令牌通道 ====================

    def _internal_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """内部令牌鉴权的 HTTP 请求（X-Internal-Token）。

        Args:
            method: GET/POST/PUT。
            path: 接口路径（如 /internal/profile）。
            params: 查询参数。
            body: 请求体（JSON）。

        Returns:
            业务响应 ``data`` 字段（类型视端点而定）。

        Raises:
            ExternalServiceError: HTTP 异常、响应解析失败或业务码非成功时。
        """
        url = f"{self._settings.business_service_url}{path}"
        headers = {
            "X-Internal-Token": self._settings.internal_token,
            "Content-Type": "application/json",
        }
        try:
            resp = requests.request(
                method,
                url,
                params=params,
                json=body,
                headers=headers,
                timeout=15,
            )
            data = resp.json()
        except Exception as exc:
            raise ExternalServiceError(
                f"内部接口请求失败: {method} {path}", cause=exc
            ) from exc
        # business-service 统一返回 Result{code,msg,data}，成功码为 200
        if data.get("code") != _SUCCESS_CODE:
            raise ExternalServiceError(
                f"内部接口返回错误: {data.get('code')} {data.get('msg', '')}".strip()
            )
        return data.get("data")

    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户求职画像。

        Args:
            user_id: 用户 ID。

        Returns:
            画像字典（含 targetPosition/cityPreference/education/school/major 等），
            无画像时返回 None。
        """
        return self._internal_request(
            "GET", "/internal/profile", params={"userId": user_id}
        )

    def get_latest_resume(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户最新简历。

        Args:
            user_id: 用户 ID。

        Returns:
            简历字典（含 id/resumeTitle/originalContent/optimizedContent 等），
            无记录时返回 None。
        """
        return self._internal_request(
            "GET", "/internal/resumes/latest", params={"userId": user_id}
        )

    def get_latest_ability(self, user_id: int) -> Optional[list]:
        """获取用户各维度最新能力画像。

        Args:
            user_id: 用户 ID。

        Returns:
            能力快照字典列表（每项含 dimension/dimensionScore/evaluation/
            snapshotDate 等），无记录时返回 None。
        """
        return self._internal_request(
            "GET", "/internal/abilities/latest", params={"userId": user_id}
        )

    def get_interview_detail(
        self, user_id: int, interview_id: int
    ) -> Optional[Dict[str, Any]]:
        """获取面试详情（含全部持久化问答），用于短期记忆重建。

        Args:
            user_id: 归属用户 ID（business 服务层据此校验记录归属）。
            interview_id: 面试记录 ID。

        Returns:
            面试详情字典（含 interviewType / status / messages 等，
            messages 每项含 role / messageType / content）；
            记录不存在或不属于该用户时由 business 抛业务错误。
        """
        return self._internal_request(
            "GET",
            f"/internal/interviews/{interview_id}",
            params={"userId": user_id},
        )

    def create_resume(
        self,
        user_id: int,
        resume_title: str,
        original_content: str,
        target_position_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建简历记录。

        Args:
            user_id: 用户 ID。
            resume_title: 简历标题。
            original_content: 原始简历文本。
            target_position_name: 目标岗位名称（可选）。

        Returns:
            创建后的简历字典（含 id）。
        """
        # 键名映射：snake_case → camelCase（对齐 InternalResumeCreateDTO）
        body = {
            "userId": user_id,
            "resumeTitle": resume_title,
            "originalContent": original_content,
        }
        if target_position_name:
            body["targetPositionName"] = target_position_name
        return self._internal_request("POST", "/internal/resumes", body=body)

    def update_resume(
        self,
        user_id: int,
        resume_id: int,
        **fields: Any,
    ) -> Dict[str, Any]:
        """更新简历记录。

        Args:
            user_id: 用户 ID（用于归属校验）。
            resume_id: 简历记录 ID。
            **fields: 更新字段白名单：
                - optimized_content: 优化后简历文本
                - optimization_suggestions: 优化建议
                - resume_score: 优化前评分 (0-100)
                - optimized_score: 优化后评分 (0-100)
                - status: 状态 (0=处理中, 1=已完成)

        Returns:
            更新后的简历字典。
        """
        # 键名映射：snake_case → camelCase（对齐 InternalResumeUpdateDTO）
        _FIELD_MAP = {
            "optimized_content": "optimizedContent",
            "optimization_suggestions": "optimizationSuggestions",
            "resume_score": "resumeScore",
            "optimized_score": "optimizedScore",
            "status": "status",
        }
        body: Dict[str, Any] = {"userId": user_id}
        for snake_key, camel_key in _FIELD_MAP.items():
            if snake_key in fields:
                body[camel_key] = fields[snake_key]
        return self._internal_request(
            "PUT", f"/internal/resumes/{resume_id}", body=body
        )

    def save_ability(
        self,
        user_id: int,
        dimension: str,
        dimension_score: int,
        evaluation: Optional[str] = None,
        snapshot_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """写入能力画像快照。

        Args:
            user_id: 用户 ID。
            dimension: 能力维度（如 专业基础/工程实践/软素养）。
            dimension_score: 维度得分 (0-100)。
            evaluation: 维度评语（可选）。
            snapshot_date: 快照日期，格式 yyyy-MM-dd（可选，默认当天）。

        Returns:
            快照字典（含 id/dimension/dimensionScore 等）。
        """
        # 键名映射：snake_case → camelCase（对齐 InternalAbilitySaveDTO）
        body: Dict[str, Any] = {
            "userId": user_id,
            "dimension": dimension,
            "dimensionScore": dimension_score,
        }
        if evaluation:
            body["evaluation"] = evaluation
        if snapshot_date:
            body["snapshotDate"] = snapshot_date
        return self._internal_request("POST", "/internal/abilities", body=body)
