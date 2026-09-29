# ===================================================================
# ai-agent-service 容器镜像
# ===================================================================
FROM docker.m.daocloud.io/library/python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/ms-playwright

# 时区配置：Asia/Shanghai
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖文件，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

# 安装 Playwright 浏览器系统依赖（手动安装，--with-deps 在 Trixie 上有字体包缺失）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 \
        libcups2t64 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
        libcairo2 libasound2t64 libxshmfence1 libx11-xcb1 \
        libxcb1 libxext6 libxfixes3 libxi6 libxrender1 \
        libdbus-1-3 libatspi2.0-0t64 libexpat1 \
        fonts-unifont && \
    rm -rf /var/lib/apt/lists/*

# 安装 Playwright Chromium 浏览器
RUN playwright install chromium

COPY app ./app

# 非 root 用户运行（安全规范）
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8001

# 端口/主机由环境变量注入，兼容 docker-compose 的 AI_AGENT_HOST/AI_AGENT_PORT
CMD ["sh", "-c", "uvicorn app.main:app --host ${AI_AGENT_HOST:-0.0.0.0} --port ${AI_AGENT_PORT:-8001}"]
