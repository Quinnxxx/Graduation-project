# 岗位采集模块（Collector）工程文档

> 适用范围：`ai-agent-service`（Python 3.10 + FastAPI + APScheduler）与 `business-service`（Java 17 + Spring Boot 3）。
> 阅读对象：论文作者 / 新人开发者；文档与 `ai-agent-service/app/collector/` 与 `business-service` 内部入库接口保持一致，字段与幂等规则以当前代码为准。

采集模块承担平台**岗位数据的持续供给**：定时 / 手动触发采集器抓取岗位源，解析为统一结构后分批推送到 business 内部入库接口（逐条幂等），每次执行落一条 `collector_log` 审计记录。当前包含一个**本地样例采集器** `sample_jobs`（链路闭环演示，仅手动触发）与一个**真实公开源采集器** `jobsys`（广东省多所高校共用的 jobsys 就业系统职位库，服务端渲染、免登录无反爬；手动触发用首次模式、定时任务用增量模式）。

---

## 1. 采集架构

### 1.1 模块划分

| 文件 | 职责 |
| --- | --- |
| `app/collector/base.py` | `BaseCollector` 抽象基类（`collect`/`parse`/`close` + `run_once` 模板方法）；`SchedulerManager`（APScheduler 定时调度） |
| `app/collector/sample_jobs.py` | `SampleJobsCollector`：本地样例源（mock），保证链路闭环可演示 |
| `app/collector/jobsys_collector.py` | `JobsysCollector`：真实公开源采集（广东省高校就业网 jobsys 职位库，列表页 + 详情页解析，首次/增量双模式） |
| `app/collector/writer.py` | `JobWriter`：分批推送 business `/internal/jobs/batch`（N=100，超时 15s） |
| `app/collector/logger.py` | `CollectorLogger`：写 `collector_log` 审计（pymysql 懒连接，雪花 id） |
| `app/api/collector_router.py` | 手动触发入口 `POST /api/v1/internal/collector/run`（X-Internal-Token 保护） |
| `app/main.py` | lifespan 装配：采集器注册表 / writer / logger / 调度器注册 |

### 1.2 数据流

```
                         ┌──────────────── ai-agent-service (8001) ─────────────────┐
                         │                                                         │
  SchedulerManager ──▶ ┌───────────┐   collect()    ┌───────────┐  parse()  ┌────────────┐
  (interval) 或         │ BaseCollector│ ────────────▶ │  原始数据   │ ─────────▶ │ 统一 DTO 记录 │
  手动触发路由           │ run_once    │   （抓取）      │ raw(HTML/  │ （清洗）    │ 列表          │
                         │ 模板方法      │              │ JSON/list) │           └─────┬──────┘
                         └───────────┘               └───────────┘                 │
                                                                                    │ JobWriter.publish()
                                                                                    │ 分批 POST /internal/jobs/batch
                                                                                    ▼
  ┌────────────────────────────────── business-service (8080) ───────────────────────────────────┐
  │ X-Internal-Token constant-time 比对 ──▶ InternalJobController ──▶ InternalJobService 逐条幂等: │
  │    job_hash 已存在 ──▶ skipped │ 不存在 ──▶ 插入 created │ 唯一键冲突 ──▶ skipped │ 异常 ──▶ failed │
  └───────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   │ 写入 job_position（uk_job_hash 唯一键）
                                                   ▼
             CollectorLogger.record_log() ──▶ collector_log（每次执行写 1 条审计）
```

`BaseCollector.run_once()` 为模板方法，任何采集器复用同一骨架：

```python
def run_once(self) -> List[Dict[str, Any]]:
    try:
        raw = self.collect()      # ① 抓取原始数据
        records = self.parse(raw)  # ② 解析为统一结构
        return records
    except CollectorError:
        raise                    # 采集业务异常透传（含状态码/原因）
    except Exception as exc:
        raise CollectorError(f"采集器 {self.name} 执行失败", cause=exc)
```

**采集入库统一契约**（`InternalJobItemDTO`）：`jobTitle / companyName / city / salaryRange / jobDetails / link / publishDate`；`categoryId / extCompany` 为采集侧附加信息，当前表无对应列，暂不落库。

---

## 2. 幂等机制

### 2.1 job_hash 唯一键

`job_position.job_hash`（`CHAR(32)`，唯一键 `uk_job_hash`）为岗位去重指纹，规则在 Java 侧 `InternalJobServiceImpl.computeJobHash()` 与表字段注释保持一致：

```
job_hash = MD5(companyName | jobTitle | city | link)
```

- 四个字段按 `|` 拼接后取 **32 位小写 MD5**；
- 任一字段为空时以空串参与拼接（`StringUtils.defaultString`）；
- 键内包含 `city` 与 `link`，**同岗位不同城市 / 不同链接可区分**。

### 2.2 逐条幂等语义（business 侧）

`POST /internal/jobs/batch`（一次 1-200 条）逐条处理，全程不整批回滚：

1. 先按 `job_hash` 查询 `count`——已存在（含逻辑删除，`@TableLogic` 自动过滤）→ `skipped++`；
2. 不存在 → 插入；`DuplicateKeyException`（并发 / 逻辑删记录仍占唯一键）→ `skipped++` 兜底；
3. 其他异常 → `failed++` 并记明细日志。

**双保险**：插入前的 count 预判 + 唯一键兜底，保证同批 / 跨批重复 hash 永不重复进表。响应汇总 `{created, skipped, failed}`。

### 2.3 实测演示

重复触发同一采集器，入库只发生一次：

```bash
# 首次（10 条均为新记录）
curl -X POST "http://localhost:8001/api/v1/internal/collector/run?name=sample_jobs" \
     -H "X-Internal-Token: campus-recruit-internal-token"
# → data: {total: 10, created: 10, skipped: 0, failed: 0}

# 幂等重放（同 10 条再次触发）
curl -X POST "http://localhost:8001/api/v1/internal/collector/run?name=sample_jobs" \
     -H "X-Internal-Token: campus-recruit-internal-token"
# → data: {total: 10, created: 0, skipped: 10, failed: 0}
```

SQL 复核：`SELECT COUNT(*), COUNT(DISTINCT job_hash) FROM job_position WHERE source_url LIKE 'https://example.com/jobs/sample-%'` → `10 / 10`（10 条且 hash 全唯一）。

---

## 3. 采集器清单

| 采集器 | `name` | `source` | 类型 | 调度方式 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| `SampleJobsCollector` | `sample_jobs` | 本地样例源（mock） | mock | 仅手动 | ✅ 演示链路闭环 |
| `JobsysCollector` | `jobsys` | 广东省高校学生就业信息网(jobsys) | real | 仅手动（首次模式，10 页/校） | ✅ 真实岗位入库 |
| `JobsysCollector` | `jobsys_incremental` | 广东省高校学生就业信息网(jobsys) | real | 定时（每日 02:00，`SCHEDULER_ENABLED` 控制） | ✅ 幂等增量（2 页/校） |

### 3.1 SampleJobsCollector（样例源，必通闭环）

- `collect()`：返回内置 10 条校园 / 实习岗位样例（Java 后端 / 前端 / 测试 / 算法 / 产品 / 运维 / 数据 / 嵌入式 / 安全 / HR），字段对齐 `InternalJobItemDTO`，模拟真实源响应体；**接入真实源时仅替换 `collect()`**（返回同样结构的列表即可），parse / 入库 / 日志无需改动；
- `parse(raw)`：缺省字段补空串；文本去两端空白；`link` 超长截断至 500（与 business `@Size(max=500)` 对齐）；`jobTitle` / `companyName` 必填缺失的行直接丢弃；
- `close()`：无外部资源，空实现。

### 3.2 JobsysCollector（真实公开源，广东高校就业网 jobsys 职位库）

**数据源**：广东省多所高校共用的 jobsys 就业系统（`cdn.jobsys.cn`），纯服务端渲染 HTML、无需登录、无反爬、字段高度结构化；一个解析器即可覆盖多所共用该校招系统的院校。站点清单（`SITES`）覆盖广东金融学院、广东外语外贸大学、仲恺农业工程学院、电子科技大学中山学院、广州航海学院、广东职业技术学院 6 校。

**采集流程**（`collect()`）：

1. 逐站点翻列表页 `GET {base_url}/web/Index/job-list?p={page}`，解析 `a.job-block`（职位名 / 发布时间 / 公司 / 薪资 / 学历 / 行业 / 地点 / 福利 / 详情链接）；
2. 逐条抓详情页 `GET {detail_url}`，取完整职位名与正文（`.content`）；
3. 请求间隔 1.5s（`REQUEST_INTERVAL`，礼貌采集）；单页无数据即停止翻页；连续 3 页失败终止该校采集。

**规模配置**：`FIRST_RUN_PAGES=10`（首次全量，约 200 条/校）、`INCREMENTAL_PAGES=2`（增量，约 40 条/校），由构造参数 `incremental` 决定，对应注册表中的 `jobsys` / `jobsys_incremental`；正文截断上限 `MAX_TEXT_LENGTH=20000`。

**解析要点**（`parse()`）：职位名 / 公司名任一为空的行直接丢弃；`jobCategory` 由 `CATEGORY_KEYWORDS` 按职位名关键词推断；`city` 由地点文本正则提取（优先 `XX市`、回退 `XX省`）；`publishDate` 优先取详情页完整日期，回退列表页 `MM/DD`（`MM>=9` 取当年，否则取次年）；学历 / 行业 / 地点 / 福利以 `【…】` 头部并入 `jobDetails`；`sourceChannel` 固定 `jobsys`。

网络失败抛 `CollectorError(5007)`（含状态码与原因），由调度下游统一降级捕获；`close()` 释放 httpx 会话。

**局限（如实说明）**：列表页职位名可能被截断，依赖详情页补全；列表页时间仅 `MM/DD` 无年份，跨年推断（`MM>=9` 取当年）存在边界误差；`update_count` 恒为 0，幂等仅覆盖"已存在跳过"，无字段更新与下架同步（见 §7.3）。

---

## 4. 调度与手动触发

### 4.1 SchedulerManager（APScheduler）

`AsyncIOScheduler`，时区 `Asia/Shanghai`：

- `add_collector_job(collector, interval_seconds=None, job_id=None)`：`interval` 触发器；`max_instances=1` + `coalesce=True` 防重入；`replace_existing=True`；`job_id` 缺省 `collector:{name}`；
- `start()` / `shutdown()` 幂等，失败抛 `CollectorError`。

**main.py 装配**（示例）：

```python
collectors = {
    "sample_jobs": SampleJobsCollector(settings),
    "jobsys": JobsysCollector(settings, incremental=False),  # 手动触发用首次模式（10 页）
    "jobsys_incremental": JobsysCollector(settings, incremental=True),  # 定时任务用增量模式（2 页）
}
app.state.collectors = collectors
if settings.scheduler_enabled:
    scheduler.add_callable_job(
        partial(run_collector, "jobsys_incremental"),
        job_id="collector:jobsys", trigger="cron", hour=2, minute=0,
    )
    scheduler.start()
```

- `sample_jobs` 与 `jobsys`（首次模式）**仅手动触发**，不注册定时任务（样例与全量数据无需重复采集）；
- `jobsys_incremental`（同源增量模式）**注册每日 02:00 cron 定时**（`job_id=collector:jobsys`），是否真正调度由 `SCHEDULER_ENABLED` 门控，默认关闭。

### 4.2 手动触发入口

```bash
POST /api/v1/internal/collector/run?name=sample_jobs|jobsys|jobsys_incremental
Header: X-Internal-Token: <AI_INTERNAL_TOKEN>
```

- **鉴权**：复用 `agent_router._verify_internal_token`，令牌与 `AI_INTERNAL_TOKEN` 不一致 → **HTTP 401**；
- `name=sample_jobs`：`run_once` → `JobWriter.publish()` 分批推送 → 落审计日志 → 返回 `{collector, source, total, created, skipped, failed, duration_ms}`；**推送彻败**（business 不可达等）抛 `CollectorError(5007)`，先落 status=3 失败审计行再按业务码返回，不崩；
- `name=jobsys`（或 `jobsys_incremental`）：抓取广东高校就业网 jobsys 职位库 → 逐条幂等入库 → 返回 `{collector, source, total, created, skipped, failed, duration_ms}`；
- 未知采集器 → `code=40400`。

### 4.3 令牌鉴权两端闭环

| 端 | 校验方式 | 失败表现 |
| --- | --- | --- |
| ai-agent 手动触发路由 | 头比对（`_verify_internal_token`） | HTTP 401 |
| business `/internal/jobs/batch` | `MessageDigest.isEqual` **constant-time** 比对（防时序侧信道） | 业务码 `1006 TOKEN_INVALID`，不落库 |

`/internal/**` 已在 `WebMvcConfig` 放行，**不经过用户 JWT**——内部接口仅面向采集 Agent 系统调用。

---

## 5. 配置清单（环境变量）

| 环境变量 | 默认值 | Settings 字段 | 说明 |
| --- | --- | --- | --- |
| `COLLECTOR_INTERVAL` | `3600` | `collector_interval` | 定时触发间隔（秒，下限 60） |
| `SCHEDULER_ENABLED` | `false` | `scheduler_enabled` | 是否启动 APScheduler 调度器 |
| `BUSINESS_SERVICE_URL` | `http://localhost:8080` | `business_service_url` | business 内部入库接口地址 |
| `AI_INTERNAL_TOKEN` | `campus-recruit-internal-token` | `internal_token` | `X-Internal-Token` 令牌，**生产必须覆盖默认值** |
| `MYSQL_HOST` | `localhost` | `mysql_host` | `collector_log` 落库连接 |
| `MYSQL_PORT` | `3306` | `mysql_port` | 同上 |
| `MYSQL_DATABASE` | `campus_recruit` | `mysql_database` | 同上 |
| `MYSQL_USERNAME` | `root` | `mysql_username` | 同上 |
| `MYSQL_PASSWORD` | 空 | `mysql_password` | 同上 |

---

## 6. 审计日志（collector_log）

真实表结构以 `docs/sql/init.sql` 第 11 张表为准：

| 字段 | 语义 | 写入来源 |
| --- | --- | --- |
| `collector_name` | 采集器名称 | 采集器类属性 |
| `source_channel` | 来源渠道 | `type` 参数（`mock` / `real`） |
| `total_count` / `new_count` / `update_count` / `fail_count` | 总数 / 新增 / 更新 / 失败 | 写入器汇总 |
| `status` | **1 成功 / 2 部分成功 / 3 失败** | 任务契约状态归一化 |
| `error_msg` | 错误 / 备注（task_id、汇总 JSON 并入此处，表无对应列） | remark 参数 |
| `start_time` / `end_time` / `cost_ms` | 起止时间与耗时（毫秒） | 单次执行 |

**状态映射**（任务契约 → 表）：`0 失败 → 3`、`1 成功 → 1`、`2 部分成功 → 2`。

写入使用与 `KnowledgeService` 一致的 **pymysql 懒连接**（首次建连、进程内复用、断开自动重连）+ 应用层雪花主键；**写库失败仅 `logger.warning`，绝不抛出**——日志是增强能力，不阻断采集主链路。示例（success / failure）：

```sql
-- 成功（status=1, total=10, new=10）
INSERT INTO collector_log (collector_name, source_channel, total_count, new_count,
    update_count, fail_count, status, error_msg, start_time, end_time, cost_ms)
VALUES (雪花id, 'sample_jobs', 'mock', 10, 10, 0, 0, 1, '{"created":10,"skipped":0,"failed":0}', ...);

-- business 不可达（status=3, error_msg 记录批量入库失败原因）
... VALUES (..., 'sample_jobs', 'mock', 10, 0, 0, 0, 3,
    '批量入库请求失败: http://localhost:8080（[WinError 10061] ...）', ...);
```

---

## 7. 局限与后续 TODO

### 7.1 真实源字段完整度

- `jobsys` 已入库真实岗位，但仍需归一：列表页职位名截断依赖详情页补全、列表页时间无年份（跨年推断 `MM>=9` 取当年）存在边界误差；
- 接入真实列表源后需对字段归一：薪资原文 → `salary_min/max` 结构化（当前仅落 `salary_note`）、学历要求、发布时间缺失补默认、`link` 去重归一；
- 采集契约中 `categoryId / extCompany` 表无对应列，暂不落库（保留在 DTO 中供后续表结构演进）。

### 7.2 反爬与合规边界

- 当前策略：**仅访问无需登录、无反爬的公开页面**（广东高校就业网 jobsys 职位库）；请求携带常规浏览器 UA，遵守 1.5s 请求间隔礼貌采集；不深度抓取全站，单校连续 3 页失败即终止；
- 若目标站点风控升级（IP 限频 / 验证码），需引入限频退避与合规的代理轮换策略，并重新评估 robots / 服务条款边界——**不得绕过反爬强行抓取**。

### 7.3 增量更新策略（TODO）

- 当前 `update_count` 恒为 `0`：幂等仅覆盖"已存在跳过"，**无字段更新与下架同步**；
- 后续可在 `job_hash` 命中时对 `salaryRange / jobDetails / publishDate` 做内容比对并 `update`，对已消失的岗位标记 `status=0` 下架；
- 可在采集侧为 `SampleJobsCollector.collect()` 增加时间戳缓存，实现"仅抓取 publishDate 增量"的增量采集。

---

## 8. 验证记录（已实测）

| 场景 | 结果 |
| --- | --- |
| 无 token 触发 | HTTP 401 |
| `sample_jobs` 首次 | `{total:10, created:10, skipped:0, failed:0}`；`job_position` 10 条，`job_hash` 全唯一 |
| `sample_jobs` 幂等重放 | `{created:0, skipped:10, failed:0}` |
| `collector_log` 成功行 | `status=1, total_count=10, new_count=10, cost_ms>0` |
| 停 business 后触发 `sample_jobs` | 响应 `code=5007`（`批量入库请求失败: ...无法连接。`），`collector_log` 落 `status=3` 失败行，服务不崩 |
| `jobsys` 真实采集（2026-10-08） | 6 站 × 10 页 = 1200 条，返回 `{collector:"jobsys", total:1200, created:636, skipped:200, failed:364, duration_ms:2392377}`（约 40 分钟）；`collector_log` 落 `source_channel=real`、`status=2` 行 |
| `jobsys` 失败原因 | 364 条失败为容器时钟回拨（`Clock moved backwards. Refusing to generate id for ~6.3s`）导致 MyBatis-Plus 雪花 ID 生成异常，属运行环境问题，非采集/解析逻辑缺陷（解析成功 1200/1200） |
| `tech_platform`（已废弃）触发 | 返回 `{"code":40400,"message":"未知采集器: tech_platform"}`，与更新后注释一致 |