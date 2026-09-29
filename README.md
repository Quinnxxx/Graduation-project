# campus-recruit-ai-platform

校园招聘 AI 平台：面向校园招聘场景的一站式平台，采用轻量微服务架构，由 Spring Boot 业务后端、Python AI Agent 服务、Vue3 前端三大业务服务，以及 MySQL、Redis、Milvus 等中间件组成，全部通过 Docker Compose 统一编排部署。

## 技术栈

| 模块 | 技术栈 | 说明 |
| --- | --- | --- |
| business-service | Java 17 + Spring Boot 3.2.10 + MyBatis-Plus 3.5.5 | 业务后端服务（含 Knife4j 4.4.0 接口文档） |
| ai-agent-service | Python 3.10 + FastAPI 0.109.2 + LangChain/LangGraph + Milvus RAG | AI Agent 服务（人岗匹配 / 简历解析 / 模拟面试 / 复盘沉淀 / 三级记忆 / 知识库两阶段检索） |
| frontend | Vue 3 + TypeScript + Vite + Pinia + Ant Design Vue | 前端项目 |
| MySQL | 8.0.36 | 关系型数据库 |
| Redis | 7.2.4 | 缓存与消息中间件 |
| Milvus | v2.3.15 | 向量数据库（向量检索） |
| MinIO | RELEASE.2023-03-20 | Milvus 依赖的对象存储 |
| Attu | v2.3.10 | Milvus 可视化工具 |

## 目录结构

```
campus-recruit-ai-platform/
├── business-service/          # Spring Boot 业务后端服务（controller/service/mapper/entity/dto/vo/config/common/exception/utils；含 Dockerfile）
├── ai-agent-service/          # Python AI Agent 服务
│   ├── app/
│   │   ├── api/               # FastAPI 路由（健康检查 / RAG 知识库管理 / 检索）
│   │   ├── agents/            # Agent 实现与注册表
│   │   ├── graph/             # LangGraph 图定义与状态
│   │   ├── rag/               # RAG 核心（向量化 / 分块 / 知识库服务 / 精排）
│   │   ├── llm/               # LLM 工厂（模型统一经阿里云百炼接入）
│   │   ├── memory/            # 三级记忆（短期 Redis / 长期 MySQL+Milvus / 工作记忆）
│   │   ├── tools/             # 工具集
│   │   ├── collector/         # 校招信息采集模块
│   │   ├── config/            # 配置管理（Settings，全量 env 化）
│   │   ├── utils/             # 工具类与异常体系
│   │   └── main.py            # 服务启动入口
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/                  # Vue3 + TS + Ant Design Vue 前端项目（7 大功能模块，含 Dockerfile）
├── docker/                    # 公共容器配置与环境变量文件
│   ├── env/                   # 各服务环境变量（env_file 注入）
│   └── mysql/init/            # MySQL 首次启动初始化脚本
├── docs/                      # 项目文档（含 SQL 建表 / 演示数据 / 验证脚本）
├── volumes/                   # 容器数据持久化目录（自动生成）
├── docker-compose.yml         # 根编排文件
└── README.md                  # 项目总说明
```

## 环境要求

- Docker Engine >= 20.10
- Docker Compose v2（`docker compose` 子命令）
- 内存建议 >= 8GB（Milvus 单机模式运行需 4GB 以上）
- 操作系统：Linux / macOS / Windows（Docker Desktop 或 WSL2）

## 启动步骤

1. 进入项目根目录：

   ```bash
   cd campus-recruit-ai-platform
   ```

2. **一键启动全部服务**（中间件 + 业务服务）：

   ```bash
   docker compose up -d --build
   ```

   > 首次启动会构建镜像（约 5-10 分钟），后续启动使用缓存秒级完成。

3. 查看服务状态：

   ```bash
   docker compose ps
   ```

4. 停止服务（保留数据）：

   ```bash
   docker compose down
   ```

   > 注意：`docker compose down -v` 会同时删除 `./volumes/` 下的全部数据，请谨慎使用。

## 服务端口说明

| 服务 | 容器名 | 端口 | 账号 / 说明 |
| --- | --- | --- | --- |
| MySQL | campus-mysql | 3306 | root / 123456，默认库 campus_recruit |
| Redis | campus-redis | 6379 | 密码 123456 |
| Milvus | campus-milvus | 19530 | 向量数据库 gRPC 端口（依赖 campus-milvus-etcd / campus-milvus-minio） |
| MinIO | campus-milvus-minio | 9000 / 9001 | minioadmin / minioadmin（9001 为控制台） |
| Attu | campus-attu | 8000 | Milvus 可视化界面（浏览器访问） |
| business-service | campus-business-service | 8080 | Spring Boot 后端（Java 17 + Spring Boot 3） |
| ai-agent-service | campus-ai-agent-service | 8001 | AI Agent 服务（Python 3.10 + FastAPI） |
| frontend | campus-frontend | 5173 | Vue3 前端（Nginx 托管，容器内 80） |

## 数据库（MySQL 8.0.36，库名 `campus_recruit`）

共 11 张表，初始化脚本位于 `docs/sql/init.sql`（首次启动由 `docker/mysql/init/` 自动执行）。

| 表名 | 用途 | 关键索引 / 约束 |
| --- | --- | --- |
| `sys_user` | 用户账号 | 唯一键 `uk_username` |
| `sys_role` | 角色 | — |
| `sys_user_role` | 用户-角色关联 | — |
| `sys_menu` | 菜单权限 | — |
| `sys_role_menu` | 角色-菜单关联 | — |
| `job_position` | 校招岗位（采集入库目标） | 唯一键 `uk_job_hash`（`job_hash = MD5(公司\|岗位\|城市\|链接)`，幂等去重） |
| `resume` | 用户简历 | — |
| `interview_session` | 面试会话 | — |
| `interview_record` | 面试对话记录 | — |
| `ability_profile` | 能力画像（5 维度，源于面试复盘） | — |
| `user_memory` | 长期记忆（三级记忆之长期层） | 唯一键 `uk_user_hash (user_id, content_hash)`（跨进程幂等）；`content_hash = MD5(content)` |
| `collector_log` | 采集执行审计 | 每次采集写 1 行（`status` 1 成功 / 2 部分成功 / 3 失败） |

> **`job_hash` 幂等说明**：采集入库时按 `MD5(companyName|jobTitle|city|link)` 计算指纹，`uk_job_hash` 唯一键保证同批 / 跨批重复 hash 永不重复进表；business 侧 `InternalJobServiceImpl` 先 count 预判再 insert，`DuplicateKeyException` 兜底。
>
> **`user_memory` 幂等说明**：长期记忆写入时按 `MD5(content)` 计算 `content_hash`，`uk_user_hash` 唯一键保证同一用户同一内容只保留一条；配合相似度去重（Cosine ≥ 0.90）拦截近似重复。

## AI 服务特性

- **多模型统一接入**：全部大模型经阿里云百炼（OpenAI 兼容接口）接入，平台级密钥统一管理；各 Agent 独立模型名，替换模型仅需修改 `.env` 中对应变量，零代码改动：
  - `LLM_JOB_MODEL` / `LLM_RESUME_MODEL` / `LLM_DEFAULT_MODEL`：qwen3.7-flash-2026-07-15（通义 Flash 快速模型，首 token 延迟低）
  - `LLM_TECH_MODEL` / `LLM_HR_MODEL`：deepseek-v4-pro-0813（DeepSeek 推理，经百炼接入）
  - `EMBEDDING_MODEL`：qwen3.7-text-embedding（向量化，维度 1024）
  - `RERANK_MODEL`：qwen3.7-text-rerank（检索精排，api_key 复用平台密钥）
- **两阶段检索（RAG）**：知识库检索采用"向量召回（粗排）→ Rerank 精排"，召回量为最终返回的 3 倍（上限 30），由精排模型按语义相关性重排取 top-k，修正词面重叠干扰；可通过 `enable_rerank` 参数关闭精排（对比实验用）。精排失败自动降级为向量排序，不阻断检索。
- **三级记忆**：短期记忆（Redis，会话上下文/场景延续标记 active_agent）、长期记忆（MySQL `user_memory` 表 + Milvus `campus_recruit_user_memory` 向量集合双写，面试复盘/简历优化后由 AI 提炼沉淀，Agent 提示词自动注入【用户长期记忆】区块）、工作记忆（LangGraph State）。
- **场景路由（两级语义）**：active_agent 存活期内仅"动作型强短语"可切换场景（延续优先，面试回答含"招聘/岗位"等宽泛词不误切）；无上下文时全量关键词识别回落自由问答；命中"复盘报告/自由问答"等 chat 强短语视为场景终结并清除延续标记。

### 多 Agent 协作

Agent 之间通过**共享状态**协作：简历优化 Agent 完成后，将 5 维度能力评估（专业基础 / 工程实践 / 算法与数据结构 / 框架与中间件 / 软素养）经内部接口写入 ability_profile 表，并将求职偏好写入长期记忆；岗位推荐 Agent 在推荐前读取能力画像与长期记忆，按维度分数说明匹配理由。协作无需点对点传参，可跨会话生效，支持能力趋势分析。

## 前端功能模块（7 大菜单）

| 菜单 | 路由 | 功能 |
| --- | --- | --- |
| 工作台 | /dashboard | 欢迎卡、岗位概览（统计/类别/城市 Top10）、能力概览（雷达维度进度，跳能力画像）、快捷入口 |
| 岗位广场 | /jobs | 校招岗位多条件筛选（关键词/类别/城市/学历/薪资）、岗位详情抽屉、一键"让 AI 分析这个岗位" |
| AI求职助手 | /assistant | 四场景 Agent 对话（岗位匹配/简历优化/技术面试/HR面试）+ 自由问答、SSE 流式、历史会话、附带简历 |
| 求职画像 | /profile | 完善简历画像（目标岗位/城市/学历/技能标签等），供 AI 精准匹配 |
| 简历管理 | /resumes | 简历新建/详情/编辑（AI 优化回填）/删除，状态与评分追踪 |
| 能力画像 | /ability | echarts 能力雷达图（5 维度）+ 成长趋势折线（按维度切换），源于模拟面试复盘 |
| 模拟面试 | /interviews | 面试记录列表、进行中对话（流式+逐步持久化）、复盘页（AI 生成结构化复盘报告并沉淀长期记忆） |

## 采集模块（Collector）

平台岗位数据的持续供给：定时 / 手动触发采集器抓取岗位源，解析为统一结构后分批推送到 business 内部入库接口（逐条幂等），每次执行落 `collector_log` 审计记录。

### 数据流

```
BaseCollector.run_once()（模板方法）
  → collect() 抓取原始数据（HTML / JSON / 内置样例）
  → parse() 清洗为 InternalJobItemDTO 结构列表
  → JobWriter.publish() 按 N=100 分批 POST /internal/jobs/batch（X-Internal-Token 鉴权）
  → business 逐条幂等（job_hash 已存在 → skipped，不存在 → created，唯一键冲突 → skipped 兜底）
  → CollectorLogger.record_log() 写 collector_log 审计行
```

### 采集器清单

| 采集器 | `name` | 类型 | 调度方式 | 状态 |
| --- | --- | --- | --- | --- |
| `SampleJobsCollector` | `sample_jobs` | mock（本地样例源，10 条内置） | 仅手动 | ✅ 演示链路闭环 |
| `JobsysCollector` | `jobsys` | real（广东高校就业网 jobsys 职位库，服务端渲染、免登录无反爬） | 仅手动（首次模式，约 10 页） | ✅ 真实岗位入库 |
| `JobsysCollector` | `jobsys_incremental` | real（同源，增量模式约 2 页） | 定时（每日 02:00，`SCHEDULER_ENABLED` 控制） | ✅ 幂等增量 |

**数据源取舍说明**：BOSS 直聘 / 拉勾 / 实习僧等强反爬站点（登录态、设备指纹、自定义字体反爬）已评估放弃；
企业官网多为 SPA 动态渲染、投入产出比低。最终选用高校就业网 jobsys 系统职位库——纯服务端渲染 HTML、
无需登录、字段结构化，且一个解析器可覆盖多所共用该校招系统的院校。

### 手动触发入口

```bash
POST /api/v1/internal/collector/run?name=sample_jobs|jobsys
Header: X-Internal-Token: <AI_INTERNAL_TOKEN>
```

- 鉴权：`_verify_internal_token`（AI 侧）+ `MessageDigest.isEqual` constant-time 比对（business 侧）
- 幂等：重复触发 `sample_jobs` → `{created:0, skipped:10, failed:0}`（同批不重复入库）
- 失败降级：business 不可达时响应 `code=5007`，`collector_log` 落 `status=3` 失败行，服务不崩

> 详细工程文档见 [docs/collector.md](docs/collector.md)。

## 配置说明

- 所有中间件与业务服务配置通过 `docker/env/` 下的环境变量文件注入，实现配置外置。
- 容器数据统一持久化到 `./volumes/` 目录，删除容器不影响数据。
- 全部服务时区统一为 Asia/Shanghai，网络统一使用 campus-network 网桥。

### 关键配置项（`docker/env/ai-agent-service.env`）

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | — | 阿里云百炼 API Key（统一管理所有模型） |
| `MILVUS_USER_MEMORY_COLLECTION` | `campus_recruit_user_memory` | 长期记忆向量集合名（与知识库 `campus_recruit_docs` 独立） |
| `MEMORY_STREAM_DISTILL` | `true` | 流式对话沉淀开关；False 时仅非流式沉淀 |
| `SCHEDULER_ENABLED` | `false` | 是否启动 APScheduler 采集调度器 |
| `COLLECTOR_INTERVAL` | `3600` | 采集定时触发间隔（秒，下限 60） |
| `BUSINESS_SERVICE_URL` | `http://business-service:8080` | business 内部入库接口地址（容器网络） |
| `AI_INTERNAL_TOKEN` | `campus-recruit-internal-token` | `X-Internal-Token` 令牌，**生产必须覆盖默认值** |

### 关键配置项（`docker/env/business-service.env`）

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `AI_SERVICE_INTERNAL_TOKEN` | `campus-recruit-internal-token` | 内部接口鉴权令牌，必须与 `AI_INTERNAL_TOKEN` 一致 |
| `JWT_SECRET` | — | JWT 签名密钥，**生产必须更换为强随机密钥** |

## 安全提示

默认账号密码仅用于本地开发环境，部署到生产环境前务必修改 `docker/env/` 下的默认密码，并更换 MySQL / Redis 口令。
