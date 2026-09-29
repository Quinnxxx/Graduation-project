"""jobsys 高校就业网采集器。

采集广东省多所高校使用的 jobsys 就业系统（cdn.jobsys.cn），
该系统为纯服务端渲染 HTML、无需登录、无反爬、字段高度结构化。

.. versionadded:: 1.1
   替代原 tech_platform 采集器（数据质量不可用）。

采集规模配置（类常量）:
    - first_run_pages: 首次全量每校最多抓 10 页（约 200 条/校）
    - incremental_pages: 增量更新每校只抓前 2 页（40 条）
    - request_interval: 请求间隔 1.5 秒（礼貌采集）
"""

import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.collector.base import BaseCollector
from app.config.settings import Settings
from app.utils.exceptions import CollectorError


class JobsysCollector(BaseCollector):
    """jobsys 高校就业网采集器。

    采集广东省多所高校使用的 jobsys 就业系统职位数据。
    """

    name = "jobsys"
    source = "广东省高校学生就业信息网(jobsys)"

    # 采集规模配置
    FIRST_RUN_PAGES = 10  # 首次全量每校最多抓 10 页（约 200 条/校）
    INCREMENTAL_PAGES = 2  # 增量更新每校只抓前 2 页（40 条）
    REQUEST_INTERVAL = 1.5  # 请求间隔秒数（礼貌采集）
    MAX_TEXT_LENGTH = 20000  # 正文截断上限

    # 站点清单：配置键、学校名、base_url
    SITES = [
        {"key": "gduf", "name": "广东金融学院", "base_url": "https://jy.gduf.edu.cn"},
        {"key": "gdufs", "name": "广东外语外贸大学", "base_url": "https://career.gdufs.edu.cn"},
        {"key": "zhku", "name": "仲恺农业工程学院", "base_url": "https://job.zhku.edu.cn"},
        {"key": "zsc", "name": "电子科技大学中山学院", "base_url": "https://jyxx.zsc.edu.cn"},
        {"key": "gzhmt", "name": "广州航海学院", "base_url": "http://gzhmt.jobsys.cn"},
        {"key": "gdpt", "name": "广东职业技术学院", "base_url": "http://jy.gdpt.edu.cn"},
    ]

    # 岗位类别关键词映射
    CATEGORY_KEYWORDS = {
        "AI算法": ["算法", "AI", "人工智能", "机器学习", "深度学习", "NLP", "CV"],
        "前端开发": ["前端", "Web", "Vue", "React", "Angular"],
        "后端开发": ["后端", "Java", "Python", "Go", "服务器", "服务端", "PHP", "Node"],
        "测试": ["测试", "QA", "质量"],
        "嵌入式": ["嵌入式", "硬件", "单片机", "FPGA"],
        "产品": ["产品", "PM"],
        "运营": ["运营", "市场"],
    }

    def __init__(self, settings: Settings, incremental: bool = False) -> None:
        """初始化采集器。

        Args:
            settings: 全局配置。
            incremental: 是否为增量模式（True=2页，False=10页）。
        """
        super().__init__(settings)
        self._incremental = incremental
        self._pages_per_site = self.INCREMENTAL_PAGES if incremental else self.FIRST_RUN_PAGES
        self._client = httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )

    def collect(self) -> List[Dict[str, Any]]:
        """抓取原始数据：列表页 + 详情页 HTML。

        Returns:
            中间结构列表，每条包含学校信息、列表字段、详情字段。
        """
        all_raw: List[Dict[str, Any]] = []
        current_year = datetime.now().year
        current_month = datetime.now().month

        for site in self.SITES:
            site_name = site["name"]
            base_url = site["base_url"]
            site_key = site["key"]
            consecutive_failures = 0

            logger.info("开始采集 {} ({}), 页数={}", site_name, base_url, self._pages_per_site)

            for page in range(1, self._pages_per_site + 1):
                try:
                    list_url = f"{base_url}/web/Index/job-list?p={page}"
                    resp = self._client.get(list_url)
                    resp.raise_for_status()

                    soup = BeautifulSoup(resp.text, "html.parser")
                    job_blocks = soup.select("a.job-block")

                    if not job_blocks:
                        logger.info("{} 第{}页无数据，停止翻页", site_name, page)
                        break

                    for block in job_blocks:
                        raw_item = self._parse_list_item(block, base_url, site_name, site_key)
                        if raw_item:
                            # 抓取详情页
                            detail_url = raw_item.get("detail_url")
                            if detail_url:
                                try:
                                    time.sleep(self.REQUEST_INTERVAL)
                                    detail_resp = self._client.get(detail_url)
                                    detail_resp.raise_for_status()
                                    raw_item["detail_html"] = detail_resp.text
                                except Exception as e:
                                    logger.warning("详情页抓取失败 {}: {}", detail_url, e)

                            all_raw.append(raw_item)

                    consecutive_failures = 0
                    time.sleep(self.REQUEST_INTERVAL)

                except Exception as e:
                    consecutive_failures += 1
                    logger.warning("{} 第{}页采集失败: {}", site_name, page, e)
                    if consecutive_failures >= 3:
                        logger.warning("{} 连续3页失败，终止该校采集", site_name)
                        break

            logger.info("{} 采集完成，共{}条", site_name, len([r for r in all_raw if r.get("site_key") == site_key]))

        return all_raw

    def _parse_list_item(
        self, block: Any, base_url: str, site_name: str, site_key: str
    ) -> Optional[Dict[str, Any]]:
        """解析列表页单个职位块。

        Args:
            block: BeautifulSoup 元素（a.job-block）。
            base_url: 站点基础 URL。
            site_name: 学校名称。
            site_key: 站点配置键。

        Returns:
            中间结构字典，解析失败返回 None。
        """
        try:
            # 职位名（可能截断）
            job_name_el = block.select_one(".job-name")
            job_name = job_name_el.get_text(strip=True) if job_name_el else ""

            # 发布时间（MM/DD 格式）
            job_time_el = block.select_one(".job-time")
            job_time = job_time_el.get_text(strip=True) if job_time_el else ""

            # 公司名
            company_el = block.select_one(".job-company")
            company_name = company_el.get_text(strip=True) if company_el else ""

            # 薪资
            salary_el = block.select_one(".job-salary")
            salary = salary_el.get_text(strip=True) if salary_el else ""

            # 学历
            edu_el = block.select_one(".job-edu")
            education = edu_el.get_text(strip=True) if edu_el else ""

            # 行业与地点（second-line 有两个 job-industry）
            industry_els = block.select(".second-line .job-industry")
            industry = ""
            location = ""
            if len(industry_els) >= 1:
                industry = industry_els[0].get_text(strip=True)
            if len(industry_els) >= 2:
                location = industry_els[1].get_text(strip=True)

            # 福利
            third_line_el = block.select_one(".third-line")
            benefits = third_line_el.get_text(strip=True) if third_line_el else ""

            # 详情链接
            href = block.get("href", "")
            detail_url = ""
            if href:
                if href.startswith("http"):
                    detail_url = href
                else:
                    detail_url = f"{base_url}/web/Index/{href}"

            # 提取城市
            city = self._extract_city(location)

            return {
                "site_name": site_name,
                "site_key": site_key,
                "base_url": base_url,
                "job_name": job_name,
                "job_time": job_time,
                "company_name": company_name,
                "salary": salary,
                "education": education,
                "industry": industry,
                "location": location,
                "city": city,
                "benefits": benefits,
                "detail_url": detail_url,
            }
        except Exception as e:
            logger.warning("列表项解析失败: {}", e)
            return None

    def _extract_city(self, location: str) -> str:
        """从地点文本提取城市名。

        规则：优先匹配「XX市」取市名（去掉"市"），
        匹配不到但文本含"省"时取省名，都取不到留空。

        Args:
            location: 地点文本，如"广东省广州市越秀区"。

        Returns:
            城市名，如"广州"。
        """
        if not location:
            return ""

        # 匹配「XX市」（排除"省"字）
        city_match = re.search(r"([\u4e00-\u9fa5]{2,4}?)市", location)
        if city_match:
            city = city_match.group(1)
            # 确保不是"XX省"的一部分
            if "省" not in city:
                return city

        # 匹配「XX省」
        province_match = re.search(r"([\u4e00-\u9fa5]{2,4}?)省", location)
        if province_match:
            return province_match.group(1)

        return ""

    def _infer_category(self, job_title: str) -> str:
        """根据职位名推断岗位类别。

        Args:
            job_title: 职位名称。

        Returns:
            岗位类别，无法判定返回空字符串。
        """
        if not job_title:
            return ""

        title_lower = job_title.lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in title_lower:
                    return category
        return ""

    def _infer_publish_date(self, job_time: str, detail_html: str = "") -> str:
        """推断发布日期。

        规则：
        - 详情页存在完整日期时优先使用
        - 列表页 MM/DD 格式：MM >= 9 取当前年，MM < 9 取下一年
        - 推断失败返回空字符串

        Args:
            job_time: 列表页时间文本，如"09/22 发布"。
            detail_html: 详情页 HTML（可选）。

        Returns:
            日期字符串，格式 YYYY-MM-DD。
        """
        current_year = datetime.now().year
        current_month = datetime.now().month

        # 尝试从详情页提取完整日期
        if detail_html:
            # 匹配 YYYY-MM-DD 或 YYYY年MM月DD日
            full_date_match = re.search(
                r"(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?",
                detail_html
            )
            if full_date_match:
                year = int(full_date_match.group(1))
                month = int(full_date_match.group(2))
                day = int(full_date_match.group(3))
                try:
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except ValueError:
                    pass

        # 从列表页时间推断
        if job_time:
            # 提取 MM/DD
            time_match = re.search(r"(\d{1,2})/(\d{1,2})", job_time)
            if time_match:
                month = int(time_match.group(1))
                day = int(time_match.group(2))
                # 秋招（9月后）取当前年，春招（9月前）取下一年
                year = current_year if month >= 9 else current_year + 1
                try:
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except ValueError:
                    pass

        return ""

    def parse(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析原始数据为统一岗位字典列表。

        Args:
            raw: collect() 返回的中间结构列表。

        Returns:
            统一字段字典列表，字段名与 InternalJobItemDTO 一致。
        """
        records: List[Dict[str, Any]] = []
        failed_count = 0

        for item in raw:
            try:
                # 提取详情完整职位名
                job_title = item.get("job_name", "")
                detail_html = item.get("detail_html", "")

                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    # 尝试从详情页提取完整职位名
                    title_el = detail_soup.select_one(".job-name, h1, .position-title")
                    if title_el:
                        full_title = title_el.get_text(strip=True)
                        # 如果列表名被截断（以...结尾），使用详情页名称
                        if job_title.endswith("...") or len(full_title) > len(job_title):
                            job_title = full_title

                company_name = item.get("company_name", "")

                # 丢弃职位名或公司名为空的记录
                if not job_title or not company_name:
                    failed_count += 1
                    continue

                # 提取详情正文
                job_details = ""
                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    content_el = detail_soup.select_one(".content")
                    if content_el:
                        job_details = content_el.get_text("\n", strip=True)

                # 构建补充信息头部（学历/行业/福利）
                header_parts = []
                if item.get("education"):
                    header_parts.append(f"【学历要求】{item['education']}")
                if item.get("industry"):
                    header_parts.append(f"【行业】{item['industry']}")
                if item.get("location"):
                    header_parts.append(f"【工作地点】{item['location']}")
                if item.get("benefits"):
                    header_parts.append(f"【福利】{item['benefits']}")

                if header_parts:
                    header = "\n".join(header_parts) + "\n\n"
                    job_details = header + job_details if job_details else header

                # 截断正文
                if len(job_details) > self.MAX_TEXT_LENGTH:
                    job_details = job_details[:self.MAX_TEXT_LENGTH]

                # 推断发布日期
                publish_date = self._infer_publish_date(
                    item.get("job_time", ""),
                    detail_html
                )

                record = {
                    "jobTitle": job_title.strip(),
                    "companyName": company_name.strip(),
                    "jobCategory": self._infer_category(job_title),
                    "city": item.get("city", "").strip(),
                    "salaryRange": item.get("salary", "").strip(),
                    "jobDetails": job_details.strip(),
                    "publishDate": publish_date,
                    "link": item.get("detail_url", "").strip(),
                    "sourceChannel": "jobsys",
                }
                records.append(record)

            except Exception as e:
                logger.warning("记录解析失败: {}", e)
                failed_count += 1

        logger.info(
            "jobsys 解析完成: success={}, failed={}",
            len(records),
            failed_count,
        )
        return records

    def run_once(self) -> List[Dict[str, Any]]:
        """执行一次完整采集。

        Returns:
            本次采集的结构化记录。
        """
        try:
            raw = self.collect()
            records = self.parse(raw)
            logger.info(
                "采集完成: collector={}, records={}",
                self.name,
                len(records),
            )
            return records
        except Exception as exc:
            raise CollectorError(
                f"采集器 {self.name} 执行失败", cause=exc
            ) from exc

    def close(self) -> None:
        """释放采集器资源。"""
        try:
            self._client.close()
        except Exception as e:
            logger.warning("jobsys 客户端关闭异常: {}", e)
