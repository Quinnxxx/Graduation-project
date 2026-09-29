"""岗位搜索工具（LangChain 协议）。

包装 BusinessServiceClient.get_jobs，查询在招校招岗位。
"""

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class SearchJobsInput(BaseModel):
    """岗位搜索输入参数。"""

    keyword: Optional[str] = Field(default=None, description="搜索关键词，如 后端、Java")
    job_category: Optional[str] = Field(default=None, description="岗位类别，如 后端开发/AI算法")
    work_city: Optional[str] = Field(default=None, description="工作城市，如 广州")
    page_num: Optional[int] = Field(default=1, description="页码，默认1")
    page_size: Optional[int] = Field(default=10, description="每页条数，默认10，上限20")


class SearchJobsTool(BaseTool):
    """岗位搜索工具。

    何时调用：用户询问岗位推荐、岗位分析、找工作时。
    """

    name: str = "search_jobs"
    description: str = (
        "搜索校招在招岗位库，支持关键词、岗位类别、城市过滤。"
        "返回岗位列表（含公司、薪资、学历要求等）。"
    )
    args_schema: Type[SearchJobsInput] = SearchJobsInput

    business_client: Any = None  # BusinessServiceClient

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        keyword: Optional[str] = None,
        job_category: Optional[str] = None,
        work_city: Optional[str] = None,
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> str:
        if self.business_client is None:
            return "[工具执行失败] 业务服务不可用"

        try:
            result = self.business_client.get_jobs(
                keyword=keyword,
                job_category=job_category,
                work_city=work_city,
                page_num=page_num or 1,
                page_size=min(page_size or 10, 20),
            )
        except Exception as exc:
            return f"[工具执行失败] 岗位查询异常: {exc}"

        total = result.get("total", 0)
        jobs = result.get("list", [])

        if total == 0:
            return "未找到匹配的岗位，请尝试放宽搜索条件（如更换关键词、城市）"

        lines = [f"共 {total} 条岗位："]
        for job in jobs[:10]:
            name = job.get("positionName", "未知")
            company = job.get("companyName", "未知")
            city = job.get("workCity", "未知")
            salary = job.get("salaryNote") or "面议"
            edu = job.get("educationText") or "不限"
            lines.append(f"- {name} | {company} | {city} | {salary} | 学历:{edu}")

        return "\n".join(lines)

    async def _arun(
        self,
        keyword: Optional[str] = None,
        job_category: Optional[str] = None,
        work_city: Optional[str] = None,
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> str:
        return self._run(keyword, job_category, work_city, page_num, page_size)
