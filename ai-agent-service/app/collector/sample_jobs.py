"""本地样例采集器：SampleJobsCollector。

基于 :class:`BaseCollector` 实现，数据源为内置本地样例（mock），保证
采集链路（抓取 -> 解析 -> 幂等入库 -> 日志）可完整闭环演示。真实源
接入时仅需替换 :meth:`collect` 的实现（返回同样结构的列表即可），
其余（parse / 入库 / 日志）无需改动。
"""

import copy
from typing import Any, Dict, List

from loguru import logger

from app.collector.base import BaseCollector
from app.config.settings import Settings

# 采集入库字段统一契约（与 business /internal/jobs/batch 的 InternalJobItemDTO 对齐）：
# jobTitle / companyName / city / salaryRange / jobDetails / link / publishDate / jobCategory
# jobCategory 为岗位类别（落 job_position.job_category），按样例真实内容如实归类
_SAMPLE_JOBS: List[Dict[str, Any]] = [
    {
        "jobTitle": "Java 后端开发工程师（校招）",
        "companyName": "星辰科技（示例）",
        "city": "北京",
        "jobCategory": "后端开发",
        "salaryRange": "18K-28K·14薪",
        "jobDetails": "负责核心业务系统后端研发，参与高并发服务压测与优化，要求熟悉 Spring Boot 与 Redis。",
        "link": "https://example.com/jobs/sample-java-backend",
        "publishDate": "2026-09-01",
    },
    {
        "jobTitle": "前端开发工程师（实习）",
        "companyName": "星绘网络（示例）",
        "city": "上海",
        "jobCategory": "前端开发",
        "salaryRange": "15K-22K·13薪",
        "jobDetails": "负责 Web 端产品页面与中后台系统开发，熟悉 Vue3 / TypeScript 优先。",
        "link": "https://example.com/jobs/sample-frontend",
        "publishDate": "2026-09-02",
    },
    {
        "jobTitle": "测试开发工程师（校招）",
        "companyName": "云启软件（示例）",
        "city": "广州",
        "jobCategory": "测试",
        "salaryRange": "13K-20K·14薪",
        "jobDetails": "负责自动化测试框架建设与质量保障，掌握接口/UI 自动化与性能压测。",
        "link": "https://example.com/jobs/sample-test-dev",
        "publishDate": "2026-09-03",
    },
    {
        "jobTitle": "算法工程师（机器学习方向）",
        "companyName": "智航数据（示例）",
        "city": "深圳",
        "jobCategory": "AI算法",
        "salaryRange": "25K-40K·15薪",
        "jobDetails": "负责推荐 / 风控场景的模型训练与上线，要求扎实的机器学习基础与代码能力。",
        "link": "https://example.com/jobs/sample-algo",
        "publishDate": "2026-09-05",
    },
    {
        "jobTitle": "产品经理（校招）",
        "companyName": "嘉禾互娱（示例）",
        "city": "杭州",
        "jobCategory": "产品",
        "salaryRange": "14K-20K·13薪",
        "jobDetails": "负责 B 端产品需求分析与推进，撰写 PRD 并协调研发按期交付。",
        "link": "https://example.com/jobs/sample-pm",
        "publishDate": "2026-09-06",
    },
    {
        "jobTitle": "运维开发工程师（校招）",
        "companyName": "磐石云（示例）",
        "city": "成都",
        "jobCategory": "运维",
        "salaryRange": "12K-19K·13薪",
        "jobDetails": "负责基础设施自动化与可观测性建设，熟悉 Linux / Docker / CI/CD。",
        "link": "https://example.com/jobs/sample-ops",
        "publishDate": "2026-09-08",
    },
    {
        "jobTitle": "数据开发工程师（校招）",
        "companyName": "数能信息（示例）",
        "city": "武汉",
        "jobCategory": "数据开发",
        "salaryRange": "15K-24K·14薪",
        "jobDetails": "负责离线与实时数仓建设，熟悉 Hive / Spark / Flink 优先。",
        "link": "https://example.com/jobs/sample-data",
        "publishDate": "2026-09-10",
    },
    {
        "jobTitle": "嵌入式软件工程师（校招）",
        "companyName": "芯桥电子（示例）",
        "city": "西安",
        "jobCategory": "嵌入式开发",
        "salaryRange": "16K-25K·14薪",
        "jobDetails": "负责车载 / IoT 设备嵌入式软件研发，熟悉 C/C++ 与 RTOS。",
        "link": "https://example.com/jobs/sample-embedded",
        "publishDate": "2026-09-12",
    },
    {
        "jobTitle": "安全工程师（校招）",
        "companyName": "盾安网安（示例）",
        "city": "南京",
        "jobCategory": "信息安全",
        "salaryRange": "17K-26K·14薪",
        "jobDetails": "负责安全应急响应与漏洞挖掘，具备渗透测试或攻防经验者（CTF）优先。",
        "link": "https://example.com/jobs/sample-security",
        "publishDate": "2026-09-15",
    },
    {
        "jobTitle": "HR 招聘专员（实习）",
        "companyName": "元策人力（示例）",
        "city": "远程",
        "jobCategory": "人力资源",
        "salaryRange": "6K-9K·12薪",
        "jobDetails": "协助校招全流程（简历初筛 / 面试安排 / Offer 沟通），人力资源相关专业优先。",
        "link": "https://example.com/jobs/sample-hr",
        "publishDate": "2026-09-18",
    },
]

# 单条链接最大长度（与 business InternalJobItemDTO @Size(max=500) 对齐）
_MAX_LINK_LEN = 500
# 岗位类别最大长度（与 business InternalJobItemDTO @Size(max=32) 对齐）
_MAX_CATEGORY_LEN = 32


class SampleJobsCollector(BaseCollector):
    """本地样例源采集器（mock，链路闭环验证用）。

    Attributes:
        name: 采集器唯一名称（调度与手动触发均用此名）。
        source: 数据来源描述。
    """

    name: str = "sample_jobs"
    source: str = "本地样例源（mock）"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

    def collect(self) -> List[Dict[str, Any]]:
        """返回内置样例列表（模拟真实源响应体）。

        Returns:
            样例原始记录列表。

        Note:
            接入真实源时仅替换本方法：请求数据源并返回同构列表即可，
            parse 与后续写入链路保持不变。
        """
        logger.info("样例采集器 collect: 内置样例 {} 条", len(_SAMPLE_JOBS))
        return copy.deepcopy(_SAMPLE_JOBS)

    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        """将原始记录映射为入库契约结构（含清洗）。

        - 缺省字段补空串；
        - 文本去两端空白，习惯性统一；
        - link 超长截断至 500 字符（与 business 侧校验对齐）；
        - jobCategory 超长截断至 32 字符（与 business 侧校验对齐）。

        Args:
            raw: :meth:`collect` 返回值（样例 dict 列表）。

        Returns:
            结构化记录列表，字段与 InternalJobItemDTO 对齐。
        """
        records: List[Dict[str, Any]] = []
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("jobTitle", "") or "").strip()
            company = str(item.get("companyName", "") or "").strip()
            if not title or not company:
                continue  # 必填缺失的行直接丢弃
            link = str(item.get("link", "") or "").strip()
            if len(link) > _MAX_LINK_LEN:
                link = link[:_MAX_LINK_LEN]
            category = str(item.get("jobCategory", "") or "").strip()
            if len(category) > _MAX_CATEGORY_LEN:
                category = category[:_MAX_CATEGORY_LEN]
            records.append(
                {
                    "jobTitle": title,
                    "companyName": company,
                    "city": str(item.get("city", "") or "").strip(),
                    "salaryRange": str(item.get("salaryRange", "") or "").strip(),
                    "jobDetails": str(item.get("jobDetails", "") or "").strip(),
                    "link": link,
                    "publishDate": str(item.get("publishDate", "") or "").strip(),
                    "jobCategory": category,
                    "sourceChannel": "sample_jobs",
                }
            )
        logger.debug("样例采集器 parse: 有效记录 {}", len(records))
        return records

    def close(self) -> None:
        """本地样例源无外部资源，空实现。"""