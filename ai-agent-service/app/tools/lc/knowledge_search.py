"""知识库检索工具（LangChain 协议）。

包装 KnowledgeService.search，支持按文档类型过滤和 top_k 限制。
用于获取专业知识（面经、简历模板、面试技巧）。
"""

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class KnowledgeSearchInput(BaseModel):
    """知识库检索输入参数。"""

    query: str = Field(description="检索问题，由模型根据任务自行构造")
    doc_type: Optional[int] = Field(
        default=None,
        description="文档类型：1=技术面经, 2=简历模板, 3=HR/面试技巧；可空=不限",
    )
    top_k: Optional[int] = Field(default=3, description="返回条数，默认3，上限5")


class KnowledgeSearchTool(BaseTool):
    """知识库检索工具。

    何时调用：需要专业知识支撑时（面经、简历模板、面试技巧）。
    """

    name: str = "knowledge_search"
    description: str = (
        "检索校招求职知识库，包含技术面经、简历模板、HR面试技巧等专业内容。"
        "输入检索问题，返回相关文档片段。"
    )
    args_schema: Type[KnowledgeSearchInput] = KnowledgeSearchInput

    knowledge_service: Any = None  # KnowledgeService 或 None

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        query: str,
        doc_type: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> str:
        if self.knowledge_service is None:
            return "[工具执行结果] 知识库暂不可用"

        try:
            top_k = min(top_k or 3, 5)
            results = self.knowledge_service.search(query, top_k=top_k, doc_type=doc_type)
        except Exception as exc:
            return f"[工具执行失败] 知识库检索异常: {exc}"

        if not results:
            return "未检索到相关内容，请换一种表述"

        lines = []
        for item in results[:top_k]:
            title = item.get("doc_title", "未知来源")
            content = item.get("content", "")
            # 截断至约 300 字
            if len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"[来源:{title}] {content}")
        return "\n\n".join(lines)

    async def _arun(
        self,
        query: str,
        doc_type: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> str:
        return self._run(query, doc_type, top_k)
