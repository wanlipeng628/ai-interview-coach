FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com

WORKDIR /app

# curl 用于容器内健康检查/调试；psycopg[binary] 自带二进制，无需额外编译依赖
# 国内服务器访问 deb.debian.org 太慢，换成阿里云镜像源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖描述文件，利用 Docker 层缓存
COPY pyproject.toml ./
COPY app ./app
COPY database ./database
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install .

EXPOSE 8010

# 单 worker，适配小内存服务器
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
