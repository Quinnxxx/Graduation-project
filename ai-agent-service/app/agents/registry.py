"""Agent 注册表。

统一管理全部 Agent 实例，以 ``agent.name`` 为唯一键注册与查找。
4 个具体 Agent（job / resume / tech / hr）在后续批次实现后统一注册，
图编排层通过本注册表按意图路由到对应 Agent。
"""

from typing import Dict, List, Optional

from app.agents.base import BaseAgent
from app.config.settings import Settings


class AgentRegistry:
    """Agent 注册表。

    Attributes:
        _agents: Agent 名称到实例的映射。
        _settings: 全局配置（供后续按需创建 Agent 使用）。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化注册表。

        Args:
            settings: 全局配置。
        """
        self._settings = settings
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """注册 Agent，以 agent.name 为唯一键。

        Args:
            agent: Agent 实例。

        Raises:
            ValueError: 同名 Agent 已注册时。
        """
        if agent.name in self._agents:
            raise ValueError(f"Agent {agent.name} 已注册")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        """按名称获取 Agent。

        Args:
            name: Agent 名称。

        Returns:
            Agent 实例，未注册返回 None。
        """
        return self._agents.get(name)

    def all(self) -> List[BaseAgent]:
        """获取全部已注册 Agent。

        Returns:
            Agent 实例列表。
        """
        return list(self._agents.values())

    def names(self) -> List[str]:
        """获取全部已注册 Agent 名称。

        Returns:
            Agent 名称列表。
        """
        return list(self._agents.keys())
