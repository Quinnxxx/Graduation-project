"""长期记忆写入工具（LangChain 协议）。

包装 LongTermMemory.save，用于沉淀用户稳定的偏好/经历/能力特点。
"""

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class SaveMemoryInput(BaseModel):
    """记忆写入输入参数。"""

    content: str = Field(description="值得跨会话记住的事实，一句话概括")
    memory_type: Optional[int] = Field(
        default=5,
        description="记忆类型：1=求职偏好, 2=项目经历, 3=能力特点, 4=面试表现, 5=其他",
    )


class SaveMemoryTool(BaseTool):
    """长期记忆写入工具。

    何时调用：发现用户稳定的偏好/经历/能力特点时，值得跨会话记住。
    """

    name: str = "save_memory"
    description: str = (
        "将用户的重要信息写入长期记忆，跨会话保留。"
        "适用于记录用户的求职偏好、项目经历、能力特点等稳定事实。"
    )
    args_schema: Type[SaveMemoryInput] = SaveMemoryInput

    user_id: int = 0
    long_term_memory: Any = None  # LongTermMemory 或 None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, content: str, memory_type: Optional[int] = None) -> str:
        if self.long_term_memory is None:
            return "[工具执行结果] 记忆功能暂不可用"

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在已有事件循环中，创建任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.long_term_memory.save(
                            str(self.user_id),
                            content,
                            memory_type=memory_type or 5,
                            importance=3,
                            source="Agent 沉淀",
                        ),
                    )
                    future.result(timeout=10)
            else:
                asyncio.run(
                    self.long_term_memory.save(
                        str(self.user_id),
                        content,
                        memory_type=memory_type or 5,
                        importance=3,
                        source="Agent 沉淀",
                    )
                )
        except Exception as exc:
            return f"[工具执行失败] 记忆写入异常: {exc}"

        # 截断显示前 40 字
        preview = content[:40] + "..." if len(content) > 40 else content
        return f"已记住：{preview}"

    async def _arun(self, content: str, memory_type: Optional[int] = None) -> str:
        if self.long_term_memory is None:
            return "[工具执行结果] 记忆功能暂不可用"

        try:
            await self.long_term_memory.save(
                str(self.user_id),
                content,
                memory_type=memory_type or 5,
                importance=3,
                source="Agent 沉淀",
            )
        except Exception as exc:
            return f"[工具执行失败] 记忆写入异常: {exc}"

        preview = content[:40] + "..." if len(content) > 40 else content
        return f"已记住：{preview}"
