# AI Interview Coach

AI Interview Coach 是一个面向 Java 开发者的 AI 面试陪练系统。项目目标是帮助候选人在接近真实面试的对话环境中练习表达、暴露薄弱知识点，并在面试结束后获得结构化复盘报告。

当前仓库是 Web MVP 版本，包含 FastAPI 后端、Vue3 前端、PostgreSQL 数据库设计、Redis 基础设施预留，以及兼容 OpenAI 接口的大模型接入能力。

## 核心能力

- 创建 Java 岗位模拟面试
- 支持填写简历文本作为面试上下文
- AI 面试官进行互动式提问和追问
- 根据用户回答决定继续追问、切换方向或结束面试
- 面试过程中不展示评分和标准答案
- 完整记录面试会话与问答内容
- 面试结束后生成结构化报告
- 支持查看历史面试记录
- 支持查看完整问答、AI 评价、参考答题要点和参考答案
- 支持报告中的薄弱知识点、改进建议、推荐训练方向和关键问答证据

## 技术栈

后端：

- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis
- OpenAI-compatible LLM Client
- AgentScope 预留

前端：

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Axios
- Element Plus
- ECharts

## 项目结构

```text
ai-interview-coach/
+-- backend/
|   +-- app/
|   |   +-- api/                 # FastAPI 路由
|   |   +-- application/         # 应用服务与 DTO
|   |   +-- domain/              # 领域实体与仓储协议
|   |   +-- infrastructure/      # 数据库、仓储、缓存、LLM、Agent
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
- Application 层：负责编排业务用例，例如开始面试、提交回答、结束面试、生成报告。
- Domain 层：定义领域实体、仓储协议和核心业务约束。
- Infrastructure 层：实现数据库访问、Repository、Redis、LLM Client 和 Agent。
- Shared 层：放置配置、日志、统一异常和通用响应结构。

前端采用按职责拆分的工程结构：

- `views`：页面级组件。
- `components`：可复用业务组件与图表组件。
- `stores`：Pinia 状态管理。
- `api`：后端接口调用封装。
- `types`：前后端交互类型和页面数据类型。

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

后端环境变量示例文件：

```text
backend/.env.example
```

首次启动时复制一份：

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

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0

LLM_PROVIDER=sensenova
LLM_API_KEY=
LLM_BASE_URL=https://api.sensenova.cn/compatible-mode/v1
LLM_MODEL=SenseChat-5
```

注意：真实的 `.env` 文件、数据库密码和大模型 API Key 不要提交到 GitHub。

## 数据库初始化

项目当前使用 PostgreSQL。

新库初始化可以执行：

```text
backend/database/schema.sql
```

已有数据库升级可以按需执行：

```text
backend/database/migrations/
```

当前核心表：

- `positions`：岗位表
- `interview_sessions`：面试会话表
- `interview_messages`：面试消息表
- `interview_answer_reviews`：单轮回答隐藏复盘表
- `interview_reports`：面试报告表

## API 概览

面试相关：

- `POST /api/interview/start`：开始面试
- `GET /api/interview/history`：查询面试历史
- `GET /api/interview/{session_id}`：查询面试会话
- `GET /api/interview/{session_id}/messages`：查询面试消息
- `POST /api/interview/{session_id}/answer`：提交回答并获取下一题
- `POST /api/interview/{session_id}/finish`：结束面试
- `GET /api/interview/{session_id}/review`：查询完整问答复盘

报告相关：

- `GET /api/interview/reports`：查询报告列表
- `GET /api/interview/{session_id}/report`：查询报告详情
- `POST /api/interview/{session_id}/report/generate`：生成面试报告

## Agent 设计

系统目前包含两个核心 Agent：

### InterviewerAgent

负责模拟技术面试官：

- 基于岗位、简历和历史问答生成下一题
- 根据用户回答决定继续追问、切换方向或结束面试
- 每次只问一个问题
- 面试过程中不展示评分、不讲解答案
- 同步生成本轮回答复盘，但只落库，不展示给候选人

隐藏复盘结构包括：

- 回答评价
- 参考答题要点
- 参考答案
- 回答等级
- 模型原始 JSON

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

## 当前 MVP 边界

当前已包含：

- Java 模拟面试主流程
- AI 面试官互动追问
- 面试会话落库
- 面试消息落库
- 单轮回答隐藏复盘
- 面试历史
- 面试报告
- 报告列表与详情
- 前端 Dashboard、模拟面试、报告、历史、能力画像、专项训练页面

暂未包含：

- 用户登录与权限体系
- 简历文件解析
- 多岗位配置后台
- 知识图谱
- 个性化推荐系统
- 异步报告任务队列
- 运营管理后台
- 企业多租户能力

## 路线图

P0：核心闭环

- 完成模拟面试、问答记录、报告生成、历史复盘
- 保证前后端接口稳定
- 保证数据库表结构完整

P1：体验增强

- 用户体系
- 简历文件上传与解析
- 面试中断恢复
- 报告证据链增强
- 更稳定的大模型输出校验

P2：训练体系

- 个性化训练计划
- 能力画像从真实历史数据生成
- 异步报告生成
- Prompt 回归测试
- 不同岗位模板配置

P3：产品化

- 管理后台
- 多租户与团队管理
- 企业版数据看板
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

请先执行：

```text
backend/database/schema.sql
```

或者执行 `backend/database/migrations/` 下对应迁移文件。

### 大模型调用失败

请检查：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- 当前网络是否能访问模型服务商

## License

License TBD.
