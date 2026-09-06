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

## Current scope

This project currently contains infrastructure and routing skeletons only. Business logic is intentionally not implemented yet.
