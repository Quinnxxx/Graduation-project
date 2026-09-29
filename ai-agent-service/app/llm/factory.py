"""LLM 客户端工厂。

依据 :class:`Settings` 中的平台级配置（API Key / Base URL）与各 Agent 模型名，
创建 langchain :class:`ChatOpenAI` 对话模型与 :class:`OpenAI` Embedding 客户端。

设计约定：
- 模型 / 平台 / 密钥全部来自配置，后期替换模型只需修改 ``.env``；
- Embedding 客户端只传入 api_key 与 base_url，模型名由调用处在请求时指定；
- 通过 :func:`get_llm_factory` 获取进程级单例。
"""

from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.config.settings import Settings
from app.utils.exceptions import ConfigError


class LLMFactory:
    """LLM 客户端工厂。

    依据 Agent 名称返回对应平台的对话模型配置（模型名 / 密钥 / 地址 /
    温度 / 最大 token 均由 :meth:`Settings.get_llm_config` 提供），
    并支持创建 Embedding 向量化客户端。

    Attributes:
        _settings: 全局配置。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化工厂。

        Args:
            settings: 全局配置。
        """
        self._settings = settings

    def create_chat_llm(self, agent_name: str) -> ChatOpenAI:
        """创建指定 Agent 的对话模型实例。

        模型 / 平台 / 密钥全部来自配置，后期替换模型只需修改 ``.env``
        中对应的 LLM_*_MODEL 或平台 Key，零代码改动。

        Args:
            agent_name: Agent 名称（job / resume / tech / hr / default）。

        Returns:
            langchain ChatOpenAI 实例。

        Raises:
            ConfigError: 对应平台 API Key 未配置时。
        """
        cfg = self._settings.get_llm_config(agent_name)
        if not cfg["api_key"]:
            raise ConfigError(
                f"Agent[{agent_name}] 未配置 API Key，请在 .env 设置对应平台 Key"
            )
        return ChatOpenAI(
            model=cfg["model"],
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
            timeout=self._settings.llm_timeout,
            max_retries=2,
        )

    def create_embedding(self) -> OpenAI:
        """创建 Embedding 向量化客户端。

        仅传入 api_key 与 base_url，模型名由调用处在请求时指定，
        便于后期替换向量化模型时无需改动工厂。

        Returns:
            openai OpenAI 客户端实例。

        Raises:
            ConfigError: Embedding API Key 未配置时。
        """
        cfg = self._settings.get_embedding_config()
        if not cfg["api_key"]:
            raise ConfigError("未配置 Embedding API Key")
        return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


@lru_cache(maxsize=1)
def get_llm_factory() -> LLMFactory:
    """获取 LLM 工厂单例（进程内缓存）。

    Returns:
        LLMFactory 实例。
    """
    from app.config.settings import get_settings

    return LLMFactory(get_settings())
