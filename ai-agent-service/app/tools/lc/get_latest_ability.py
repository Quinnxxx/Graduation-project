"""最新能力画像查询工具（LangChain 协议）。

包装 BusinessServiceClient.get_latest_ability，读取用户各维度最新能力评估，
供岗位推荐时按能力分数说明匹配理由。
"""

from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel


class GetLatestAbilityInput(BaseModel):
    """最新能力画像查询无输入参数（userId 由构造函数注入）。"""
    pass


class GetLatestAbilityTool(BaseTool):
    """最新能力画像查询工具（无参数）。

    何时调用：岗位推荐前，读取用户各维度能力评估以说明匹配理由。
    """

    name: str = "get_latest_ability"
    description: str = (
        "获取用户各能力维度的最新评估（维度名、分数、评语）。"
        "用于岗位推荐时按能力画像说明匹配理由。"
    )
    args_schema: Type[GetLatestAbilityInput] = GetLatestAbilityInput

    business_client: Any = None  # BusinessServiceClient
    user_id: int = 0

    class Config:
        arbitrary_types_allowed = True

    def _run(self) -> str:
        if self.business_client is None:
            return "[工具执行失败] 业务服务不可用"

        try:
            abilities = self.business_client.get_latest_ability(self.user_id)
        except Exception as exc:
            return f"[工具执行失败] 能力画像查询异常: {exc}"

        if not abilities:
            return "用户暂无可参考的能力评估数据"

        lines = []
        for item in abilities:
            dimension = item.get("dimension", "未知维度")
            score = item.get("dimensionScore")
            evaluation = item.get("evaluation")
            if evaluation:
                lines.append(f"{dimension}: {score}（{evaluation}）")
            else:
                lines.append(f"{dimension}: {score}")
        return "\n".join(lines)

    async def _arun(self) -> str:
        return self._run()
