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
# 依赖层：只依赖 pyproject.toml 的 dependencies，代码变更不会使这一层失效
COPY pyproject.toml ./
RUN python -c "import tomllib,subprocess,sys;deps=tomllib.load(open('pyproject.toml','rb'))['project']['dependencies'];sys.exit(subprocess.call([sys.executable,'-m','pip','install',*deps]))"

# 代码层：日常改代码只重建以下这一层（依赖层命中缓存，几秒完成）
COPY app ./app
COPY database ./database
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8010

# 单 worker，适配小内存服务器
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
