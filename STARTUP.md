# 校园招聘AI平台 - 启动指南

## 启动顺序（每次开发前按顺序操作）

### 第1步：启动中间件（Docker Desktop）

- 双击桌面 **Docker Desktop** 图标
- 等待左下角鲸鱼图标变绿（约30秒）
- Docker 会自动启动所有中间件容器（MySQL、Redis、Milvus、MinIO、Attu）

验证：浏览器打开 http://localhost:8000（Attu），能登录就说明中间件OK

---

### 第2步：启动后端 business-service

- 打开 IDEA
- 打开项目 `E:\Graduation project\campus-recruit-ai-platform(doubao)\business-service`
- 找到 `BusinessServiceApplication.java`
- 点击绿色三角形运行

验证：浏览器打开 http://localhost:8080/doc.html，能看到接口文档就说明OK

> ⚠️ business-service 基于 Spring Boot 3.x，**必须使用 JDK 17** 编译/运行（JDK 8 会报 class file version 错误）。
> 命令行启动前先执行 `mvn -v` 确认 Runtime 为 17；IDEA 中在 Project Structure → SDK 选择 JDK 17。

---

### 第3步：启动前端 frontend

打开一个 **PowerShell 窗口**，执行：

```bash
cd "E:\Graduation project\campus-recruit-ai-platform(doubao)\frontend"
npm run dev
```

看到 `Local: http://localhost:5173/` 后，浏览器访问该地址

> ⚠️ 这个窗口不能关，关了前端就停了

---

### 第4步：启动 AI Agent（可选，做AI功能时才需要）

再打开一个 **新的 PowerShell 窗口**，执行：

```bash
cd "E:\Graduation project\campus-recruit-ai-platform(doubao)\ai-agent-service"
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

看到 `Uvicorn running on http://0.0.0.0:8001` 就成功了

> ⚠️ 这个窗口也不能关
> 验证：浏览器打开 http://localhost:8001/docs

---

## 服务端口一览

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | http://localhost:5173 | 用户看到的界面 |
| 后端接口文档 | http://localhost:8080/doc.html | Knife4j 接口调试 |
| AI Agent 文档 | http://localhost:8001/docs | FastAPI Swagger |
| Attu (Milvus可视化) | http://localhost:8000 | 向量数据库管理 |
| MySQL | localhost:3306 | root / 123456 |
| Redis | localhost:6379 | 密码 123456 |

## 登录账号

| 用户名 | 密码 |
|--------|------|
| admin | 123456 |

---

## 常见问题

**Q: 为什么要开4个窗口？不能一键启动吗？**
A: 开发阶段这样是标准做法。每个服务独立调试、独立看日志，出问题好定位。以后部署上线时会用 Docker Compose 一键启动所有服务。

**Q: 电脑重启后要重新启动哪些？**
A: Docker Desktop 一般开机自启。后端要在IDEA重新点运行，前端和AI Agent要重新跑命令。

**Q: 某个窗口关了怎么办？**
A: 重新按上面的步骤启动那个服务就行，其他服务不用动。

**Q: 启动容器时报 `WSL is unresponsive`，或 Redis 报 AOF I/O error、Milvus/etcd 崩溃怎么办？**
A: 这是 WSL2 子系统僵死（常见于长时间运行、休眠唤醒或磁盘曾被写满），命令行通常无法恢复。直接**重启电脑**，再启动 Docker Desktop 即可；容器数据存放在挂载卷中，一般不会丢失。

**Q: C 盘空间不足会影响 Docker 吗？**
A: 会。Docker 的虚拟磁盘 `docker_data.vhdx` 默认在 C 盘，空间过满可能导致容器异常。可定期清理 npm 缓存（`npm cache clean --force`）与无用镜像（`docker image prune`），并保证 C 盘留有数 GB 以上空闲。

**Q: 命令行 `mvn` 报版本不对或编译失败？**
A: 先执行 `mvn -v` 查看 Java 版本，必须为 JDK 17。若系统默认还是 JDK 8，可在当前终端临时设置 JAVA_HOME 指向 JDK 17 目录后再运行；IDEA 用户直接使用 Project SDK=17 即可，不受系统默认影响。

**Q: 采集/写入偶发 `Clock moved backwards` 导致批量入库失败？**
A: 这是 WSL2/Docker 环境下的容器时钟回拨（休眠唤醒、NTP 步进校正、VM 恢复时可能发生），会触发雪花 ID 的时钟保护。
   除代码侧已内置的容错 ID 生成器外，环境侧建议：避免长时间休眠后再直接使用 Docker；必要时在 PowerShell 执行
   `wsl --shutdown` 后重启 Docker Desktop 使其重新同步时间。生产 Linux 环境通常使用 chrony 平滑校正（slew），
   该问题概率显著低于本地 WSL2。
