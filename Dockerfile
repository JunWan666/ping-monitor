# 多阶段构建 - 前端构建阶段
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# 最终运行阶段
FROM python:3.11-slim

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制后端代码
COPY backend/ ./backend/

# 安装Python依赖
RUN pip install --no-cache-dir -r backend/requirements.txt

# 从构建阶段复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动后端服务
CMD ["python", "backend/main.py"]
