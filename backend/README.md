# AI Interview Coach Backend

FastAPI backend skeleton for the AI interview coach MVP.

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload
```

Open:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## API Overview

### Resume Management

- `POST /api/resume/upload`：上传简历文件（支持 `.txt/.md/.pdf/.docx`，成功返回 201 和 `ResumeProfileResponse`，不支持/空/损坏文件返回 400）
- `GET /api/resume/profile`：获取当前用户简历档案
- `PUT /api/resume/profile`：保存当前用户简历档案

### Resume Assistant（对话式引导生成简历）

按固定顺序分节引导：`BASIC → EDUCATION → WORK → PROJECT → SKILL → INTENT → DONE`，
一次只问一个问题，同一分节最多追问 2 轮，用户说「没有」跳节、说「帮我生成吧」直接结束。

- `POST /api/resume/assistant/start`：开始引导，返回第一个问题（201）
- `POST /api/resume/assistant/{draft_id}/answer`：提交回答，返回下一个问题或 `ready_to_finalize`；
  草稿为 `COMPLETED` 时仍可继续提交，回答会作为补充并入对应分节，不会重新推进分节
- `POST /api/resume/assistant/{draft_id}/finalize`：生成 Markdown 简历并写入 `resume_profiles`（可迭代：
  每次都重新生成并覆盖当前用户的默认简历，`profile_id` 保持不变）
- `GET /api/resume/assistant/{draft_id}`：查询草稿状态（刷新 / 续聊），同样返回 `ready_to_finalize`

结束指令按整句匹配（去标点后整句由「帮我生成吧 / 差不多了 / 就这样」等短语构成），
叙述句里的「就这样」「差不多了」不会被误判为结束。

提示：`answer` / `finalize` 在 LLM 调用失败时内部走确定性兜底（不返回 502），
`start` 不调用 LLM；服务端不会因 LLM 抖动返回 5xx。

错误提示统一为中文文案：草稿不存在返回 404，回答为空返回 400，不会把内部英文信息透给前端。

QA 复现脚本：`bash scripts/qa_resume_assistant.sh`（需先启动后端，依赖 curl + python）。

数据表 `resume_drafts` 已同步到 `database/schema.sql` 与 `database/migrations/20261007_add_resume_drafts.sql`。

## Current scope

This project currently contains infrastructure and routing skeletons only. Business logic is intentionally not implemented yet.
