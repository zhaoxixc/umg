FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 TZ=Asia/Shanghai

# mysqldump / mysql 客户端用于应用内备份与恢复
# 优先使用阿里云镜像源加速，失败时回退官方源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends default-mysql-client \
    && rm -rf /var/lib/apt/lists/* \
    || (sed -i 's|mirrors.aliyun.com|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
        && apt-get update \
        && apt-get install -y --no-install-recommends default-mysql-client \
        && rm -rf /var/lib/apt/lists/*)

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
