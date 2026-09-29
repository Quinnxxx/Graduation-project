"""能力快照记录工具（LangChain 协议）。

包装 BusinessServiceClient.save_ability，记录面试各维度能力评估。
"""

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class RecordAbilityInput(BaseModel):
    """能力快照记录输入参数。"""

    dimension: str = Field(
        description="能力维度：专业基础/工程实践/算法与数据结构/框架与中间件/软素养",
    )
    dimension_score: int = Field(description="维度评分 0-100")
    evaluation: Optional[str] = Field(default=None, description="维度评语，一句话")


class RecordAbilityTool(BaseTool):
    """能力快照记录工具。

    何时调用：面试结束时评估各维度能力。
    """

    name: str = "record_ability"
    description: str = (
        "记录用户在某个能力维度的表现快照，包含评分和评语。"
        "用于面试复盘时沉淀能力画像。"
    )
    args_schema: Type[RecordAbilityInput] = RecordAbilityInput

    business_client: Any = None  # BusinessServiceClient
    user_id: int = 0

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        dimension: str,
        dimension_score: int,
        evaluation: Optional[str] = None,
    ) -> str:
        if self.business_client is None:
            return "[工具执行失败] 业务服务不可用"

        # 校验评分范围
        if not 0 <= dimension_score <= 100:
            return f"[工具执行失败] 评分必须在 0-100 之间，当前: {dimension_score}"

        try:
            self.business_client.save_ability(
                self.user_id,
                dimension,
                dimension_score,
                evaluation=evaluation,
            )
        except Exception as exc:
            return f"[工具执行失败] 能力记录异常: {exc}"

        return f"已记录能力快照：{dimension} {dimension_score} 分"

    async def _arun(
        self,
        dimension: str,
        dimension_score: int,
        evaluation: Optional[str] = None,
    ) -> str:
        return self._run(dimension, dimension_score, evaluation)
