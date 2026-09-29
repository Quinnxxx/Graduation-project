"""优化简历保存工具（LangChain 协议）。

实现简历优化闭环：先查最新简历，有则更新，无则新建。
"""

from datetime import datetime
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class SaveOptimizedResumeInput(BaseModel):
    """优化简历保存输入参数。"""

    optimized_content: str = Field(description="优化后的完整简历文本")
    resume_title: Optional[str] = Field(
        default=None,
        description="简历标题，默认 'AI 优化简历-{当天}'",
    )
    target_position_name: Optional[str] = Field(default=None, description="目标岗位名称")
    suggestions: Optional[str] = Field(default=None, description="优化要点/建议")
    resume_score: Optional[int] = Field(default=None, description="优化前评分 0-100")
    optimized_score: Optional[int] = Field(default=None, description="优化后评分 0-100")


class SaveOptimizedResumeTool(BaseTool):
    """优化简历保存工具。

    何时调用：用户明确说"保存/就按这个改/存到我的简历/可以"时。
    """

    name: str = "save_optimized_resume"
    description: str = (
        "将优化后的简历保存到用户的简历库。"
        "如果用户已有简历则更新优化内容，否则新建一条记录。"
    )
    args_schema: Type[SaveOptimizedResumeInput] = SaveOptimizedResumeInput

    business_client: Any = None  # BusinessServiceClient
    user_id: int = 0

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        optimized_content: str,
        resume_title: Optional[str] = None,
        target_position_name: Optional[str] = None,
        suggestions: Optional[str] = None,
        resume_score: Optional[int] = None,
        optimized_score: Optional[int] = None,
    ) -> str:
        if self.business_client is None:
            return "[工具执行失败] 业务服务不可用"

        try:
            # 1. 先查最新简历
            latest = self.business_client.get_latest_resume(self.user_id)

            if latest and latest.get("id"):
                # 2. 有记录 → 更新
                resume_id = latest["id"]
                self.business_client.update_resume(
                    self.user_id,
                    resume_id,
                    optimized_content=optimized_content,
                    optimization_suggestions=suggestions,
                    optimized_score=optimized_score,
                    resume_score=resume_score,
                    status=1,
                )
                return f"简历已保存到「我的简历」（记录 id:{resume_id}，方式：更新）"
            else:
                # 3. 无记录 → 新建（以优化稿作为原始内容建档）
                title = resume_title or f"AI 优化简历-{datetime.now().strftime('%m%d')}"
                result = self.business_client.create_resume(
                    self.user_id,
                    title,
                    optimized_content,  # 无原始文本时以优化稿建档
                    target_position_name,
                )
                resume_id = result.get("id", "未知")
                return f"简历已保存到「我的简历」（记录 id:{resume_id}，方式：新建）"

        except Exception as exc:
            return f"[工具执行失败] 简历保存异常: {exc}"

    async def _arun(
        self,
        optimized_content: str,
        resume_title: Optional[str] = None,
        target_position_name: Optional[str] = None,
        suggestions: Optional[str] = None,
        resume_score: Optional[int] = None,
        optimized_score: Optional[int] = None,
    ) -> str:
        return self._run(
            optimized_content,
            resume_title,
            target_position_name,
            suggestions,
            resume_score,
            optimized_score,
        )
