# ai-agent-service

校园招聘 AI 平台 AI Agent 服务，基于 **Python 3.10 + FastAPI + LangGraph + LangChain** 构建，提供简历解析、智能问答、人岗匹配等 Agent 能力，向量检索基于 Milvus，记忆基于 Redis / MySQL + Milvus。

## 技术栈

| 模块 | 技术选型 |
| --- | --- |
| Web 框架 | FastAPI 0.109 + Uvicorn |
| Agent 编排 | LangGraph 0.1.10 |
| LLM 集成 | LangChain 0.2.x + langchain-openai 0.1.x |
| 向量检索 | Milvus v2.3.15（pymilvus 2.3.5） |
| 短期记忆 | Redis（滑动窗口 + TTL 过期） |
| 长期记忆 | MySQL + Milvus（骨架，待接入持久化） |
| 任务调度 | APScheduler 3.10.4（AsyncIOScheduler） |

## 目录结构

```
ai-agent-service/
├── app/
│   ├── api/          # FastAPI 接口层（路由、统一响应模型）
│   ├── agents/       # Agent 实现目录，每个 Agent 独立文件（base.py 定义基类）
│   ├── graph/        # LangGraph 图定义与状态（state.py）
│   ├── memory/       # 三级记忆：短期 / 长期 / 任务工作记忆
│   ├── rag/          # RAG 检索引擎（Milvus 连接封装 + 检索基类）
│   ├── tools/        # 工具集（工具基类，可插件化注册）
│   ├── collector/    # 校招信息采集模块（采集器基类 + 调度器）
│   ├── config/       # 统一配置管理（环境变量驱动）
│   ├── utils/        # 日志、分级异常
│   └── main.py       # 服务启动入口（中间件、路由注册、异常处理）
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## 本地启动

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Docker 启动

```bash
docker build -t ai-agent-service .
docker run -p 8001:8001 --env-file .env ai-agent-service
```

## 接口说明

| 接口 | 说明 |
| --- | --- |
| `GET /api/v1/health` | 健康检查（含 Redis / Milvus 依赖状态） |
| `GET /docs` | Swagger 接口文档（FastAPI 内置） |

## 代码规范

- PEP8 + 全量类型注解，公共类/方法 Google 风格 docstring
- 外部调用统一捕获异常并包装为分级异常（`AppError` 体系），禁止裸 `except`
- 敏感配置全部从环境变量读取，禁止硬编码
- 模块解耦：Agent / Tool / RAG / Collector 均面向抽象基类编程，支持插件化扩展
