# ===================================================================
# frontend 容器镜像（多阶段构建：Node 构建 -> Nginx 运行）
# 构建期注入后端地址：--build-arg VITE_API_BASE_URL=http://business-service:8080
# ===================================================================

# ---- Stage 1: Build ----
FROM docker.m.daocloud.io/library/node:20-alpine AS build
WORKDIR /app

# 先拷贝依赖清单，利用 Docker 层缓存
COPY package.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install

COPY . .

# 前端使用 /api 相对路径，由 nginx 反代到后端，无需构建期注入后端地址
RUN npm run build

# ---- Stage 2: Runtime ----
FROM docker.m.daocloud.io/library/nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
