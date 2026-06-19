# Alembic

PostgreSQL migration configuration for the FastAPI backend.

Common commands:

```bash
alembic revision --autogenerate -m "init schema"
alembic upgrade head
alembic downgrade -1
```
