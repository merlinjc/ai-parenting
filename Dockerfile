# AI Parenting Backend — 多阶段 Docker 镜像
#
# 使用方法：
#   docker build -t aip-backend .
#   docker run -p 8000:8000 --env-file .env aip-backend

FROM python:3.12-slim AS base

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[push]" 2>/dev/null || pip install --no-cache-dir .

# 复制应用代码
COPY src/ src/

# 数据目录
RUN mkdir -p /app/data /app/certs

# 运行
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "ai_parenting.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
