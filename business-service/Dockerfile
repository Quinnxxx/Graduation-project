# ===================================================================
# business-service 容器镜像（多阶段构建）
# 阶段一：Maven 构建；阶段二：JRE 运行
# ===================================================================

# ---- Stage 1: Build ----
FROM docker.m.daocloud.io/library/maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /app

# 配置 Maven 阿里云镜像
RUN mkdir -p /root/.m2 && echo '<?xml version="1.0" encoding="UTF-8"?><settings><mirrors><mirror><id>aliyun</id><mirrorOf>central</mirrorOf><url>https://maven.aliyun.com/repository/central</url></mirror></mirrors></settings>' > /root/.m2/settings.xml

# 先拷贝 pom.xml 提前拉取依赖，利用 Docker 层缓存
COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn clean package -DskipTests -B

# ---- Stage 2: Runtime ----
FROM docker.m.daocloud.io/library/eclipse-temurin:17-jre-alpine
WORKDIR /app

# 时区配置：Asia/Shanghai
RUN apk add --no-cache tzdata \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone
ENV TZ=Asia/Shanghai

# 非 root 用户运行（安全规范）
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

COPY --from=build /app/target/business-service.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "app.jar"]
