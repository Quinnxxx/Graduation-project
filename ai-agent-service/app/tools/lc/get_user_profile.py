"""用户画像查询工具（LangChain 协议）。

包装 BusinessServiceClient.get_user_profile，获取用户求职画像。
"""

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel


class GetUserProfileInput(BaseModel):
    """用户画像查询无输入参数（userId 由构造函数注入）。"""
    pass


class GetUserProfileTool(BaseTool):
    """用户画像查询工具（无参数）。

    何时调用：需要了解用户背景时（首轮对话、岗位推荐前）。
    """

    name: str = "get_user_profile"
    description: str = (
        "获取当前用户的求职画像，包括目标岗位、意向城市、学历、学校、专业、"
        "技能标签等。用于了解用户背景。"
    )
    args_schema: Type[GetUserProfileInput] = GetUserProfileInput

    business_client: Any = None  # BusinessServiceClient
    user_id: int = 0

    class Config:
        arbitrary_types_allowed = True

    def _run(self) -> str:
        if self.business_client is None:
            return "[工具执行失败] 业务服务不可用"

        try:
            profile = self.business_client.get_user_profile(self.user_id)
        except Exception as exc:
            return f"[工具执行失败] 画像查询异常: {exc}"

        if not profile:
            return "用户尚未填写求职画像"

        lines = ["用户求职画像："]
        if profile.get("targetPosition"):
            lines.append(f"- 目标岗位: {profile['targetPosition']}")
        if profile.get("cityPreference"):
            lines.append(f"- 意向城市: {profile['cityPreference']}")
        edu_map = {0: "其他", 1: "本科", 2: "硕士", 3: "博士"}
        edu = profile.get("education")
        if edu is not None:
            lines.append(f"- 学历: {edu_map.get(edu, '未知')}")
        if profile.get("school"):
            lines.append(f"- 学校: {profile['school']}")
        if profile.get("major"):
            lines.append(f"- 专业: {profile['major']}")
        if profile.get("graduationYear"):
            lines.append(f"- 毕业年份: {profile['graduationYear']}")
        skills = profile.get("skillTags") or []
        if skills:
            lines.append(f"- 技能: {', '.join(skills)}")
        if profile.get("careerIntention"):
            lines.append(f"- 求职意向: {profile['careerIntention'][:100]}")

        return "\n".join(lines)

    async def _arun(self) -> str:
        return self._run()
