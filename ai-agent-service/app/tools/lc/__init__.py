"""LangChain 标准协议工具层。

本目录包含 8 个 LangChain BaseTool 工具，供 ReAct Agent 通过 function calling
自主调用。所有工具遵循统一约定：

1. 继承 langchain_core.tools.BaseTool（非项目自研 BaseTool）
2. 使用 pydantic BaseModel 定义 args_schema
3. userId 由构造函数注入（不在 args_schema 中暴露给模型）
4. 异常返回结构化字符串（不抛裸异常），让模型可观察并调整
5. 返回简洁字符串/JSON，控制长度避免撑爆上下文
"""

from app.tools.lc.knowledge_search import KnowledgeSearchTool
from app.tools.lc.save_memory import SaveMemoryTool
from app.tools.lc.search_jobs import SearchJobsTool
from app.tools.lc.get_user_profile import GetUserProfileTool
from app.tools.lc.get_latest_resume import GetLatestResumeTool
from app.tools.lc.save_optimized_resume import SaveOptimizedResumeTool
from app.tools.lc.record_ability import RecordAbilityTool
from app.tools.lc.get_latest_ability import GetLatestAbilityTool

__all__ = [
    "KnowledgeSearchTool",
    "SaveMemoryTool",
    "SearchJobsTool",
    "GetUserProfileTool",
    "GetLatestResumeTool",
    "SaveOptimizedResumeTool",
    "RecordAbilityTool",
    "GetLatestAbilityTool",
]
