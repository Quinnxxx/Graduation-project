"""工具基类。

定义工具的标准调用接口 :meth:`BaseTool.run` 与元信息导出
:meth:`BaseTool.to_dict`（供 LLM function calling / Agent 提示词消费）。
所有具体工具（简历解析、岗位查询、公司搜索等）继承本类并注册到 Agent。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """工具抽象基类。

    Attributes:
        name: 工具唯一名称（Agent 调用时的标识）。
        description: 工具功能描述（供 LLM 理解何时调用）。
        parameters: 参数 JSON Schema（可选，供 LLM 生成调用参数）。
    """

    name: str = "base_tool"
    description: str = "工具描述"
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """执行工具逻辑。

        Args:
            **kwargs: 工具入参，键名与 parameters Schema 对齐。

        Returns:
            工具执行结果（字符串 / 字典 / 列表均可，按工具语义定义）。

        Raises:
            ToolError: 工具执行失败时由调用方（Agent.call_tool）统一包装。
        """

    def to_dict(self) -> Dict[str, Any]:
        """导出工具元信息。

        Returns:
            包含 name / description / parameters 的字典。
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
