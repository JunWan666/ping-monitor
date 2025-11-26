# Docker 部署说明

本目录包含Ping监控系统的Docker相关文件。

## 文件说明

- `Dockerfile` - Docker镜像构建文件
- `docker-compose.yml` - Docker Compose配置文件
- `.dockerignore` - Docker构建时忽略的文件
- `docker-start.bat` - Windows一键启动脚本
- `build_and_push.py` - 多架构镜像构建和推送脚本
- `build-and-push.bat` - Windows下运行构建脚本的批处理文件

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

## 构建和推送多架构镜像

本项目提供了自动化脚本来构建和推送支持多架构（AMD64和ARM64）的Docker镜像。

### 使用方法

1. 确保已安装Docker Desktop并启用了Buildx功能
2. 在Windows环境下，双击运行 `build-and-push.bat` 或在命令行中执行：
   ```
   cd docker
   build-and-push.bat
   ```
3. 在Linux/Mac环境下，直接运行Python脚本：
   ```
   cd docker
   python3 build_and_push.py
   ```
4. 按照提示输入Docker Hub用户名、仓库名和要构建的版本号
5. 脚本将自动构建AMD64和ARM64架构的镜像并推送到Docker Hub

### 特性

- 自动查询Docker Hub上的现有版本
- 支持交互式输入构建参数
- 自动处理版本号前缀（自动添加'v'前缀）
- 构建并推送多架构镜像（AMD64和ARM64）
- 自动创建多架构Manifest清单
- 可用于覆盖现有标签（如latest或特定版本）

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