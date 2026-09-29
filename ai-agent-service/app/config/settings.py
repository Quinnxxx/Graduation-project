"""统一配置管理。

所有配置项均从环境变量读取（支持 ``.env`` 文件，由 python-dotenv 加载），
禁止在代码中硬编码任何敏感信息。通过 :func:`get_settings` 获取全局单例。

环境变量命名与 ``docker/env/ai-agent-service.env`` 保持一致，
支持容器编排（docker-compose）与本地开发两种场景。

大模型配置设计：
- 平台级密钥（阿里云百炼）与 Agent 解耦，由环境变量注入；
- 每个 Agent 独立模型名（LLM_JOB_MODEL / LLM_RESUME_MODEL / LLM_TECH_MODEL /
  LLM_HR_MODEL / LLM_DEFAULT_MODEL），后期替换模型只需修改 ``.env``，零代码改动；
- 全部模型（通义 / DeepSeek）统一经阿里云百炼 OpenAI 兼容接口接入，
  单一密钥管理；调用方通过 :meth:`Settings.get_llm_config` 获取对应 Agent 的模型配置。
- Rerank 模型与 Embedding 模型独立配置，均 env 化可替换。
"""

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

from app.utils.exceptions import ConfigError

# 加载 .env 文件（存在时），override=True 确保 .env 覆盖系统环境变量，
# 避免旧的系统级 DASHSCOPE_API_KEY 等残留值覆盖本地 .env 中的新配置
load_dotenv(override=True)


def _get_str(key: str, default: str = "", required: bool = False) -> str:
    """读取字符串环境变量。

    Args:
        key: 环境变量名。
        default: 缺省值。
        required: 是否必填，缺失时抛出 ConfigError。

    Returns:
        环境变量值或默认值。

    Raises:
        ConfigError: 必填变量缺失时。
    """
    raw = os.getenv(key)
    if raw is not None and raw != "":
        return raw
    if required:
        raise ConfigError(f"缺少必需环境变量: {key}")
    return default


def _get_int(
    key: str,
    default: int,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    """读取整数环境变量并做范围校验。

    Args:
        key: 环境变量名。
        default: 缺省值。
        minimum: 允许最小值，None 不限制。
        maximum: 允许最大值，None 不限制。

    Returns:
        整数值。

    Raises:
        ConfigError: 值非整数或超出范围时。
    """
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {key} 不是合法整数: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"环境变量 {key} 小于最小值 {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"环境变量 {key} 大于最大值 {maximum}")
    return value


def _get_float(key: str, default: float) -> float:
    """读取浮点环境变量。

    Args:
        key: 环境变量名。
        default: 缺省值。

    Returns:
        浮点值。

    Raises:
        ConfigError: 值非浮点数时。
    """
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {key} 不是合法数字: {raw!r}") from exc


def _get_bool(key: str, default: bool) -> bool:
    """读取布尔环境变量，兼容 1/0/true/false/yes/no/on/off。

    Args:
        key: 环境变量名。
        default: 缺省值。

    Returns:
        布尔值。

    Raises:
        ConfigError: 值无法解析为布尔时。
    """
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"环境变量 {key} 不是合法布尔值: {raw!r}")


class Settings(BaseModel):
    """应用配置模型。

    字段名与 ``docker/env/ai-agent-service.env`` 的环境变量一一对应，
    通过 :meth:`Settings.from_env` 从环境变量构建。

    大模型平台配置与 Agent 模型配置解耦：平台密钥（阿里云百炼）由环境变量注入，
    各 Agent 通过 :meth:`get_llm_config` 按需取用，后期替换模型只需修改 ``.env``
    中的模型名，无需改动代码。
    """

    # ---- 应用 ----
    app_name: str = "ai-agent-service"
    app_env: str = "dev"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"
    log_dir: Optional[str] = None
    api_prefix: str = "/api/v1"

    # ---- 大模型平台（阿里云百炼，OpenAI 兼容；DeepSeek 模型亦经本平台接入） ----
    # 阿里云百炼 API Key（统一管理所有模型）
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ---- 各 Agent 模型名（均可被环境变量覆盖） ----
    # 岗位分析 Agent 模型，通义 Flash 快速模型（首 token 延迟低，适合交互）
    llm_job_model: str = "qwen3.7-flash-2026-07-15"
    # 简历优化 Agent 模型，长文本润色
    llm_resume_model: str = "qwen3.7-flash-2026-07-15"
    # 技术面试 Agent 模型，DeepSeek 推理
    llm_tech_model: str = "deepseek-v4-pro-0813"
    # HR 面试 Agent 模型
    llm_hr_model: str = "deepseek-v4-pro-0813"
    # 自由问答兜底模型
    llm_default_model: str = "qwen3.7-flash-2026-07-15"
    # 大模型请求超时时间（秒）；为岗位分析、简历诊断等复杂任务保留充足余量，
    # 默认 180，可由 LLM_TIMEOUT 覆盖
    llm_timeout: int = 180

    # ---- Embedding（向量化，RAG 检索） ----
    # 向量化模型，维度经实测确认后同步 EMBEDDING_DIM
    embedding_model: str = "qwen3.7-text-embedding"
    embedding_api_key: str = ""
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # embedding 输出维度，替换模型时按模型实际维度修改
    embedding_dim: int = 1024

    # ---- Rerank（检索精排，两阶段检索第二阶段） ----
    # 精排模型，与 Embedding 模型独立配置，均 env 化可替换
    rerank_model: str = "qwen3.7-text-rerank"
    rerank_url: str = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

    # ---- 业务服务内部调用 ----
    # 内部调用业务服务的服务账号
    service_username: str = "admin"
    service_password: str = "123456"

    # ---- 对外对话接口内部鉴权 ----
    # AI 服务内部访问令牌：business-service 转发时通过 X-Internal-Token 头携带，
    # 防止 AI 对话接口被公网直接调用；生产环境必须用 AI_INTERNAL_TOKEN 覆盖默认值
    internal_token: str = "campus-recruit-internal-token"

    # ---- Milvus ----
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "campus_recruit_docs"
    # 长期记忆向量集合（LongTermMemory 使用），与知识库集合相互独立
    milvus_user_memory_collection: str = "campus_recruit_user_memory"
    milvus_username: str = ""
    milvus_password: str = ""
    milvus_alias: str = "default"

    # ---- Redis ----
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_short_term_db: int = 1

    # ---- 短期会话记忆 ----
    short_term_ttl: int = 86400
    short_term_max_messages: int = 20

    # ---- MySQL（长期记忆持久化骨架） ----
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "campus_recruit"
    mysql_username: str = "root"
    mysql_password: str = ""

    # ---- 采集调度 ----
    scheduler_enabled: bool = False
    collector_interval: int = 3600

    # ---- 业务服务 ----
    business_service_url: str = "http://localhost:8080"

    # ---- 对话沉淀 ----
    # 流式对话链路的长期记忆沉淀开关（复盘类恒走非流式；False 时仅非流式沉淀）
    memory_stream_distill: bool = True

    # ---- 北京 HR 用户 ----
    # 北京 HR 用户标识（用于特定业务场景）
    beijing_hr_user_key: str = "1790653991382"

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量构建配置。

        Returns:
            Settings 实例。

        Raises:
            ConfigError: 环境变量缺失或非法时。
        """
        values: dict = {
            "app_name": _get_str("APP_NAME", "ai-agent-service"),
            "app_env": _get_str("APP_ENV", "dev"),
            "debug": _get_bool("DEBUG", False),
            "host": _get_str("AI_AGENT_HOST", "0.0.0.0"),
            "port": _get_int("AI_AGENT_PORT", 8001, minimum=1, maximum=65535),
            "log_level": _get_str("LOG_LEVEL", "INFO"),
            "log_dir": _get_str("LOG_DIR", "") or None,
            "api_prefix": _get_str("API_PREFIX", "/api/v1"),
            # 大模型平台（阿里云百炼，统一管理所有模型）
            "dashscope_api_key": _get_str("DASHSCOPE_API_KEY", ""),
            "dashscope_base_url": _get_str(
                "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            # 各 Agent 模型名
            "llm_job_model": _get_str("LLM_JOB_MODEL", "qwen3.7-flash-2026-07-15"),
            "llm_resume_model": _get_str("LLM_RESUME_MODEL", "qwen3.7-flash-2026-07-15"),
            "llm_tech_model": _get_str("LLM_TECH_MODEL", "deepseek-v4-pro-0813"),
            "llm_hr_model": _get_str("LLM_HR_MODEL", "deepseek-v4-pro-0813"),
            "llm_default_model": _get_str("LLM_DEFAULT_MODEL", "qwen3.7-flash-2026-07-15"),
            "llm_timeout": _get_int("LLM_TIMEOUT", 180, minimum=1),
            # Embedding
            "embedding_model": _get_str("EMBEDDING_MODEL", "qwen3.7-text-embedding"),
            "embedding_api_key": _get_str("EMBEDDING_API_KEY", ""),
            "embedding_base_url": _get_str(
                "EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            "embedding_dim": _get_int("EMBEDDING_DIM", 1024, minimum=1),
            "rerank_model": _get_str("RERANK_MODEL", "qwen3.7-text-rerank"),
            "rerank_url": _get_str(
                "RERANK_URL",
                "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
            ),
            # 业务服务内部调用
            "service_username": _get_str("SERVICE_USERNAME", "admin"),
            "service_password": _get_str("SERVICE_PASSWORD", "123456"),
            # 对外对话接口内部鉴权
            "internal_token": _get_str(
                "AI_INTERNAL_TOKEN", "campus-recruit-internal-token"
            ),
            "milvus_host": _get_str("MILVUS_HOST", "localhost"),
            "milvus_port": _get_int("MILVUS_PORT", 19530, minimum=1, maximum=65535),
            "milvus_collection": _get_str("MILVUS_COLLECTION", "campus_recruit_docs"),
            "milvus_user_memory_collection": _get_str(
                "MILVUS_USER_MEMORY_COLLECTION", "campus_recruit_user_memory"
            ),
            "milvus_username": _get_str("MILVUS_USERNAME", ""),
            "milvus_password": _get_str("MILVUS_PASSWORD", ""),
            "milvus_alias": _get_str("MILVUS_ALIAS", "default"),
            "redis_host": _get_str("REDIS_HOST", "localhost"),
            "redis_port": _get_int("REDIS_PORT", 6379, minimum=1, maximum=65535),
            "redis_password": _get_str("REDIS_PASSWORD", ""),
            "redis_db": _get_int("REDIS_DB", 0, minimum=0),
            "redis_short_term_db": _get_int("REDIS_SHORT_TERM_DB", 1, minimum=0),
            "short_term_ttl": _get_int("SHORT_TERM_TTL", 86400, minimum=60),
            "short_term_max_messages": _get_int("SHORT_TERM_MAX_MESSAGES", 20, minimum=1),
            "mysql_host": _get_str("MYSQL_HOST", "localhost"),
            "mysql_port": _get_int("MYSQL_PORT", 3306, minimum=1, maximum=65535),
            "mysql_database": _get_str("MYSQL_DATABASE", "campus_recruit"),
            "mysql_username": _get_str("MYSQL_USERNAME", "root"),
            "mysql_password": _get_str("MYSQL_PASSWORD", ""),
            "scheduler_enabled": _get_bool("SCHEDULER_ENABLED", False),
            "collector_interval": _get_int("COLLECTOR_INTERVAL", 3600, minimum=60),
            "business_service_url": _get_str("BUSINESS_SERVICE_URL", "http://localhost:8080"),
            "memory_stream_distill": _get_bool("MEMORY_STREAM_DISTILL", True),
            # 北京 HR 用户
            "beijing_hr_user_key": _get_str("BEIJING_HR_USER_KEY", ""),
        }
        try:
            settings = cls(**values)
        except Exception as exc:
            raise ConfigError(f"配置初始化失败: {exc}", cause=exc) from exc

        if not settings.dashscope_api_key:
            logger.warning("未配置阿里云百炼 API Key，LLM 能力将不可用")
        else:
            logger.info("已配置大模型平台: 阿里云百炼（dashscope）")
        return settings

    def get_llm_config(self, agent_name: str) -> dict:
        """获取指定 Agent 的大模型配置。

        全部模型统一经阿里云百炼（OpenAI 兼容）接入，单一密钥管理：
        - ``job``：岗位分析，通义模型，信息提取场景 temperature 用 0.3 保证抽取稳定；
        - ``resume``：简历优化，通义模型，长文本润色需稳定输出用 0.4；
        - ``tech``：技术面试，DeepSeek 模型（同走百炼平台），提问需逻辑严谨用 0.3；
        - ``hr``：HR 面试，DeepSeek 模型（同走百炼平台），对话需自然多变用 0.7；
        - 其他/默认：自由问答兜底，通用场景用 0.5。

        后期替换模型只需修改 ``.env`` 中的 LLM_*_MODEL，零代码改动。
        返回的是新构建的 dict，调用方修改其中的任何值都不影响 Settings 本身。

        Args:
            agent_name: Agent 名称（job / resume / tech / hr，其他视为默认）。

        Returns:
            模型配置字典：{model, base_url, api_key, temperature, max_tokens}。
        """
        config_map: dict = {
            "job": {
                "model": self.llm_job_model,
                "base_url": self.dashscope_base_url,
                "api_key": self.dashscope_api_key,
                "temperature": 0.3,
                "max_tokens": 2048,
            },
            "resume": {
                "model": self.llm_resume_model,
                "base_url": self.dashscope_base_url,
                "api_key": self.dashscope_api_key,
                "temperature": 0.4,
                # 简历优化需一次输出「诊断报告 + 完整优化稿 + JSON 结果块」，
                # 4096 在实测中超长报告时被截断导致结果块缺失，放宽到模型上限
                "max_tokens": 8192,
            },
            "tech": {
                "model": self.llm_tech_model,
                "base_url": self.dashscope_base_url,
                "api_key": self.dashscope_api_key,
                "temperature": 0.3,
                "max_tokens": 2048,
            },
            "hr": {
                "model": self.llm_hr_model,
                "base_url": self.dashscope_base_url,
                "api_key": self.dashscope_api_key,
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        }
        # 其他/默认：自由问答兜底
        return config_map.get(
            agent_name,
            {
                "model": self.llm_default_model,
                "base_url": self.dashscope_base_url,
                "api_key": self.dashscope_api_key,
                "temperature": 0.5,
                "max_tokens": 2048,
            },
        )

    def get_embedding_config(self) -> dict:
        """获取 Embedding 向量化模型配置。

        返回的是新构建的 dict，调用方修改其中的任何值都不影响 Settings 本身。

        Returns:
            Embedding 配置字典：{model, api_key, base_url, dim}。
        """
        return {
            "model": self.embedding_model,
            "api_key": self.embedding_api_key,
            "base_url": self.embedding_base_url,
            "dim": self.embedding_dim,
        }

    def get_rerank_config(self) -> dict:
        """获取 Rerank 精排模型配置。

        api_key 复用百炼平台密钥（与对话/向量模型同源），
        后期切换 rerank 模型只需修改 .env 的 RERANK_MODEL。

        Returns:
            Rerank 配置字典：{model, url, api_key}。
        """
        return {
            "model": self.rerank_model,
            "url": self.rerank_url,
            "api_key": self.dashscope_api_key,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局配置单例（进程内缓存）。

    Returns:
        Settings 实例。
    """
    return Settings.from_env()
