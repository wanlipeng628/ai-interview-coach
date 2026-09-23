# AI Interview Coach

AI Interview Coach 是一个面向 Java 开发者的 AI 模拟面试陪练系统。候选人在接近真实面试的对话环境中练习表达、暴露薄弱知识点，面试结束后获得逐轮复盘与结构化报告。项目已通过 Docker Compose 部署至阿里云 ECS，公网可访问。

## 核心能力

- 创建 Java 岗位模拟面试，支持岗位、面试方向、面试官模式、时长配置
- 支持填写简历文本作为面试上下文，AI 面试官基于简历动态追问
- AI 面试官每轮评估回答质量，决定继续追问、切换方向或结束面试
- 面试过程中不展示评分和标准答案，保持真实面试感
- 完整记录面试会话与问答内容，面试结束后生成结构化报告
- 逐轮复盘：AI 评价、参考答题要点、参考答案，历史详情页按轮次展示，支持重新生成
- 移动端响应式适配：桌面端（≥1024px）与移动端（375px+）均有完整可用体验

## 设计亮点

### 决策与生成解耦，复盘延迟异步生成

模拟面试的核心链路是"LLM 评估回答 → 决策 → 出题"。早期版本将逐轮复盘与下一题在同一次 LLM 调用中生成，导致每轮提问都要等待长文本输出，响应缓慢。重构后：

- **面试过程中**：LLM 只输出决策（continue / switch / end）与下一题，精简 Prompt 后单轮响应从同步等待完整复盘缩短至数秒级
- **面试结束后**：后台线程分批（5 轮/次）批量生成缺失轮次的复盘并落库，报告读取直接复用落库数据，不重复调用 LLM
- **幂等与覆盖**：批量生成只补缺失轮次；`POST /reviews/regenerate` 接口支持强制全量重新生成

### 容错兜底设计

- 复盘生成失败不影响主流程：报告读取自带规则模板兜底（评价/要点/答案），不依赖实时 AI 调用
- LLM API 限流（429）时自动指数退避重试，仍失败则走兜底，绝不阻塞用户请求

### 移动端适配策略

- 桌面端（≥1024px）保持改造前像素级一致，移动端适配全部收敛在 ≤1023px 媒体查询内
- 桌面表格在移动端转换为卡片布局，交互入口完整保留
- 适配质量由 AI Agent 工作流验证：开发 → QA 多视口（375/768/1024/1280/1440）Playwright 验收 → 架构审查

## 技术栈

后端：

- Python 3.11 / FastAPI / SQLAlchemy 2.x / Pydantic
- PostgreSQL（存储会话、消息、复盘、报告）
- OpenAI 兼容 LLM Client（模型可配置，当前使用 deepseek-v4-flash）
- 分层架构：API / Application / Domain / Infrastructure / Shared（接近 DDD）

前端：

- Vue 3 / TypeScript / Vite / Pinia / Vue Router
- Element Plus / ECharts / Axios

部署：

- Docker Compose / Nginx（静态托管 + 反向代理）
- 阿里云 ECS（2 核 1G 内存约束下的构建与部署优化）

## 项目结构

```text
ai-interview-coach/
+-- backend/
|   +-- app/
|   |   +-- api/                 # FastAPI 路由
|   |   +-- application/         # 应用服务与 DTO
|   |   +-- domain/              # 领域实体与仓储协议
|   |   +-- infrastructure/      # 数据库、仓储、LLM Client、Agent
|   |   +-- shared/              # 配置、日志、异常、通用响应
|   |   +-- main.py              # FastAPI 启动入口
|   +-- alembic/                 # Alembic 配置
|   +-- database/                # 数据库建表 SQL 与迁移 SQL
|   +-- tests/                   # 后端测试
|   +-- .env.example             # 环境变量示例
|   +-- pyproject.toml
+-- frontend/
|   +-- src/
|   |   +-- api/                 # Axios API 封装
|   |   +-- assets/              # 全局样式与静态资源
|   |   +-- components/          # 通用组件
|   |   +-- layouts/             # 页面布局
|   |   +-- router/              # 路由配置
|   |   +-- stores/              # Pinia 状态管理
|   |   +-- types/               # TypeScript 类型
|   |   +-- views/               # 页面视图
|   +-- package.json
|   +-- vite.config.ts
+-- .gitignore
+-- README.md
```

## 架构说明

后端采用接近 DDD 的分层结构：

- API 层：负责 HTTP 路由、参数接收、异常转换。
- Application 层：负责编排业务用例，例如开始面试、提交回答、结束面试、生成复盘与报告。
- Domain 层：定义领域实体、仓储协议和核心业务约束。
- Infrastructure 层：实现数据库访问、Repository、LLM Client 和 InterviewerAgent。
- Shared 层：放置配置、日志、统一异常和通用响应结构。

前端采用按职责拆分的工程结构：

- `views`：页面级组件。
- `components`：可复用业务组件与图表组件。
- `stores`：Pinia 状态管理。
- `api`：后端接口调用封装。
- `types`：前后端交互类型和页面数据类型。

## Agent 设计

系统目前包含两个核心 Agent：

### InterviewerAgent

负责模拟技术面试官：

- 基于岗位、简历和历史问答生成下一题
- 每轮先评估候选人回答质量，再决定继续追问、切换方向或结束面试
- 每次只问一个问题，不展示评分、不讲解答案
- 面试过程中只输出决策与问题，复盘延迟到面试结束后批量生成

### ReportAgent

负责面试结束后的最终报告：

- 总体评分
- 技术能力分析
- 表达能力分析
- 项目经验分析
- 薄弱知识点
- 改进建议
- 推荐训练方向
- 关键问答证据

报告只在面试结束后生成，避免用户在面试过程中被评分干扰。

## 快速启动

### 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

访问地址：

- Swagger 文档：`http://127.0.0.1:8010/docs`
- 健康检查：`http://127.0.0.1:8010/api/v1/health`

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- 前端页面：`http://127.0.0.1:5173`

## 环境变量

后端环境变量示例文件：`backend/.env.example`，首次启动复制一份：

```bash
copy backend\.env.example backend\.env
```

重点配置项：

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DATABASE=ai_interview_coach

LLM_PROVIDER=sensenova
LLM_API_KEY=
LLM_BASE_URL=https://token.sensenova.cn/v1
LLM_MODEL=deepseek-v4-flash
LLM_TEMPERATURE=0.7
LLM_TIMEOUT_SECONDS=60
```

注意：真实的 `.env` 文件、数据库密码和大模型 API Key 不要提交到 GitHub。

## 数据库初始化

项目使用 PostgreSQL。新库初始化执行：

```text
backend/database/schema.sql
```

已有数据库升级按需执行 `backend/database/migrations/` 下的迁移文件。

当前核心表：

- `positions`：岗位表
- `interview_sessions`：面试会话表
- `interview_messages`：面试消息表
- `interview_answer_reviews`：单轮回答复盘表（面试结束后批量落库）
- `interview_reports`：面试报告表

## API 概览

面试相关：

- `POST /api/interview/start`：开始面试
- `GET /api/interview/history`：查询面试历史
- `GET /api/interview/{session_id}`：查询面试会话
- `GET /api/interview/{session_id}/messages`：查询面试消息
- `POST /api/interview/{session_id}/answer`：提交回答并获取下一题
- `POST /api/interview/{session_id}/finish`：结束面试（触发后台批量复盘）
- `GET /api/interview/{session_id}/review`：查询完整问答复盘
- `POST /api/interview/{session_id}/reviews/regenerate`：强制重新生成全部复盘

简历相关：

- `POST /api/resume/upload`：上传简历文件（支持 `.txt/.md/.pdf/.docx`，成功返回 201，不支持/空/损坏文件返回 400）

报告相关：

- `GET /api/interview/reports`：查询报告列表
- `GET /api/interview/{session_id}/report`：查询报告详情
- `POST /api/interview/{session_id}/report/generate`：生成面试报告

## 部署

使用 Docker Compose 一键部署：

```bash
# 1. 准备环境变量（POSTGRES_PASSWORD / LLM_API_KEY 等）
cp .env.example .env

# 2. 构建并启动（数据库 + 后端 + Nginx）
docker compose up -d --build

# 3. 前端：本地构建 dist 后由 Nginx 静态托管（避免服务器 1G 内存构建 OOM）
cd frontend && npm run build
# 将 dist 内容同步到服务器 frontend/dist 后：
docker compose up -d --force-recreate web
```

部署环境为 2 核 1G 内存，因此做了针对性取舍：前端本地构建 dist、后端镜像分步构建、单 uvicorn worker、关闭 Redis 依赖，保证资源占用可控。

## 当前 MVP 边界

当前已包含：

- Java 模拟面试主流程
- AI 面试官互动追问与动态决策
- 面试会话与消息落库
- 单轮回答复盘（延迟批量生成、可重新生成）
- 面试历史与逐轮复盘详情
- 面试报告生成与列表
- 简历文件解析与上传
- 移动端响应式适配

暂未包含：

- 用户登录与权限体系
- 多岗位配置后台
- 知识图谱
- 个性化推荐系统
- 运营管理后台
- 企业多租户能力

## 路线图

P0：核心闭环（已完成）

- 模拟面试、问答记录、报告生成、历史复盘
- 前后端接口稳定、数据库表结构完整

P1：体验增强

- 用户体系
- 面试中断恢复
- 报告证据链增强
- 更稳定的大模型输出校验

P2：训练体系

- 个性化训练计划
- 能力画像从真实历史数据生成
- Prompt 回归测试
- 不同岗位模板配置

P3：产品化

- 管理后台
- 多租户与团队管理
- 可观测性与部署体系
- 权限、审计与安全增强

## 常见问题

### 后端端口被占用

换一个端口启动：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

### 前端报 `ECONNREFUSED`

通常是前端代理连接不到后端。请检查：

- 后端服务是否已启动
- 后端端口是否和 `frontend/vite.config.ts` 中的代理端口一致
- 数据库连接是否正常

### 数据库提示表不存在

请先执行 `backend/database/schema.sql`，或执行 `backend/database/migrations/` 下对应迁移文件。

### 大模型调用失败

请检查：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- 当前网络是否能访问模型服务商

## License

License TBD.
