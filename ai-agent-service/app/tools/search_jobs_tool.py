"""校招岗位查询工具。

供岗位分析 Agent（job）通过 function calling 调用，按关键词 / 岗位类别 /
工作城市检索 business-service 的在招岗位库。工具仅做参数整理与转发，鉴权与
HTTP 通信由 :class:`BusinessServiceClient` 负责，执行异常由 Agent.call_tool
统一包装为 ToolError。
"""

from typing import Any, Dict

from app.services.business_client import BusinessServiceClient
from app.tools.base import BaseTool

# 允许从 LLM 调用参数中透传的查询字段（status 固定查在招岗位，不对模型开放）
_ALLOWED_QUERY_KEYS = (
    "keyword",
    "job_category",
    "work_city",
    "page_num",
    "page_size",
)


class SearchJobsTool(BaseTool):
    """校招岗位查询工具（供岗位分析 Agent 调用）。

    通过服务账号访问 business-service 的公开岗位接口，返回在招岗位分页列表，
    供 Agent 结合用户画像做人岗匹配与岗位推荐。
    """

    name: str = "search_jobs"
    description: str = (
        "查询校招在招岗位库，支持关键词/岗位类别/城市过滤，"
        "返回岗位列表（含公司、薪资、学历要求等）"
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词，如 后端",
            },
            "job_category": {
                "type": "string",
                "description": "岗位类别，如 后端开发/前端开发/AI算法",
            },
            "work_city": {
                "type": "string",
                "description": "工作城市，如 广州",
            },
            "page_num": {
                "type": "integer",
                "description": "页码，默认1",
            },
            "page_size": {
                "type": "integer",
                "description": "每页条数，默认10",
            },
        },
    }

    def __init__(self, client: BusinessServiceClient) -> None:
        """初始化工具。

        Args:
            client: 业务服务客户端（已封装服务账号鉴权与 token 缓存）。
        """
        self._client = client

    def run(self, **kwargs: Any) -> Any:
        """执行岗位查询。

        仅透传白名单内的非空查询参数，其余参数（含模型误传的 status）忽略，
        固定查询在招岗位（status=1）。

        Args:
            **kwargs: 查询参数，键名与 :attr:`parameters` Schema 对齐：
                keyword / job_category / work_city / page_num / page_size。

        Returns:
            business-service 的 PageResult 字典：
            ``{"total", "pageNum", "pageSize", "list"}``。
        """
        query: Dict[str, Any] = {
            key: value
            for key, value in kwargs.items()
            if key in _ALLOWED_QUERY_KEYS and value is not None
        }
        return self._client.get_jobs(**query)