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

## Current scope

This project currently contains infrastructure and routing skeletons only. Business logic is intentionally not implemented yet.
