"""最新简历查询工具（LangChain 协议）。

包装 BusinessServiceClient.get_latest_resume，获取用户最新简历。
"""

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel


class GetLatestResumeInput(BaseModel):
    """最新简历查询无输入参数（userId 由构造函数注入）。"""
    pass


class GetLatestResumeTool(BaseTool):
    """最新简历查询工具（无参数）。

    何时调用：需要查看用户简历时（简历优化前）。
    """

    name: str = "get_latest_resume"
    description: str = (
        "获取用户最新一份简历，包含原始内容和优化后内容。"
        "用于查看用户现有简历。"
    )
    args_schema: Type[GetLatestResumeInput] = GetLatestResumeInput

    business_client: Any = None  # BusinessServiceClient
    user_id: int = 0

    class Config:
        arbitrary_types_allowed = True

    def _run(self) -> str:
        if self.business_client is None:
            return "[工具执行失败] 业务服务不可用"

        try:
            resume = self.business_client.get_latest_resume(self.user_id)
        except Exception as exc:
            return f"[工具执行失败] 简历查询异常: {exc}"

        if not resume:
            return "简历库中暂无简历"

        lines = [f"简历标题: {resume.get('resumeTitle', '未命名')}"]

        # 优先显示优化后内容，否则显示原始内容
        content = resume.get("optimizedContent") or resume.get("originalContent", "")
        if content:
            # 截断至约 1500 字
            if len(content) > 1500:
                content = content[:1500] + "\n...(内容已截断)"
            lines.append(f"\n简历内容:\n{content}")

        if resume.get("targetPositionName"):
            lines.append(f"\n目标岗位: {resume['targetPositionName']}")

        return "\n".join(lines)

    async def _arun(self) -> str:
        return self._run()
