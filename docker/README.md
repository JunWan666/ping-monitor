# Docker 部署说明

本目录包含Ping监控系统的Docker相关文件。

## 文件说明

- `Dockerfile` - Docker镜像构建文件
- `docker-compose.yml` - Docker Compose配置文件
- `.dockerignore` - Docker构建时忽略的文件
- `docker-start.bat` - Windows一键启动脚本

## 快速启动

### 方法一：使用Docker Compose（推荐）

```bash
# 在项目根目录执行
cd docker
docker-compose up -d
```

### 方法二：使用预构建镜像

```bash
# 拉取镜像
docker pull tannic666/ping-monitor:latest

# 运行容器
docker run -d --name ping-monitor \
  -p 8000:8000 \
  -v "$(pwd)/../data:/app/data" \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  tannic666/ping-monitor:latest
```

### 方法三：手动构建

```bash
# 在项目根目录执行
docker build -f docker/Dockerfile -t ping-monitor:local .

# 运行容器
docker run -d --name ping-monitor \
  -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  ping-monitor:local
```

## 环境变量

- `TZ` - 时区设置（默认：Asia/Shanghai）
- `DB_PATH` - 数据库文件路径（默认：/app/data/ping_monitor.db）

## 数据持久化

容器默认将数据保存在 `/app/data` 目录，建议挂载到宿主机：

```bash
-v /path/to/your/data:/app/data
```

## 访问地址

启动后访问：http://localhost:8000
