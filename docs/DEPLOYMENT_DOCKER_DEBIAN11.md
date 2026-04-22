# Debian 11 Docker 部署教程

本文适用于在 `Debian 11` 服务器上，以 `Docker` 方式部署 `Ping 监控系统`。

如果你希望尽量少手工操作，推荐直接使用仓库中的一键脚本：

```bash
sudo bash scripts/deploy-docker-debian11.sh
```

脚本会自动完成以下工作：

- 安装 Docker CE、Buildx、Compose 插件
- 配置 Docker 镜像加速
- 启动并设置 Docker 开机自启
- 拉取 `tannic666/ping-monitor:v1.5.0`
- 使用项目自带 `docker/docker-compose.yml` 启动服务

## 1. 部署前准备

建议准备：

- 一台 Debian 11 服务器
- `root` 用户，或可使用 `sudo` 的管理员账号
- 已开放服务器安全组 / 防火墙的 `8000` 端口
- 已将本项目代码上传到服务器，或使用 `git clone` 拉取项目

示例：

```bash
git clone https://gitee.com/jun-wan/ping-monitor.git
cd ping-monitor
```

## 2. 可选：先替换 Debian 软件源

如果你的服务器访问官方 Debian 源比较慢，可以先切换镜像源。

下面这组命令整理自你原来的安装笔记，适合 Debian 11：

```bash
cp /etc/apt/sources.list /etc/apt/sources.list.bak

cat > /etc/apt/sources.list <<'EOF'
deb https://repo.huaweicloud.com/debian/ bullseye main contrib non-free
deb https://repo.huaweicloud.com/debian/ bullseye-updates main contrib non-free
deb https://repo.huaweicloud.com/debian/ bullseye-backports main contrib non-free
deb https://repo.huaweicloud.com/debian-security/ bullseye-security main contrib non-free
EOF

sed -i 's/.*bullseye-backports.*/# &/' /etc/apt/sources.list
apt update
```

这一步不是必须的。如果你的服务器本身访问软件源很正常，可以直接跳过。

## 3. 一键部署方式

在项目根目录执行：

```bash
sudo bash scripts/deploy-docker-debian11.sh
```

默认行为：

- 安装 Docker
- 配置 Docker 加速
- 使用镜像 `tannic666/ping-monitor:v1.5.0`
- 以 `docker compose` 方式启动整套服务

部署完成后访问：

- 系统首页：`http://你的服务器IP:8000`
- API 文档：`http://你的服务器IP:8000/docs`

## 4. 一键脚本可选参数

### 仅安装 Docker，不部署应用

```bash
sudo bash scripts/deploy-docker-debian11.sh --install-only
```

### 跳过 Docker 安装，只部署应用

```bash
sudo bash scripts/deploy-docker-debian11.sh --deploy-only
```

### 指定镜像标签

```bash
sudo bash scripts/deploy-docker-debian11.sh --image tannic666/ping-monitor:latest
```

### 不修改 Docker 加速配置

```bash
sudo bash scripts/deploy-docker-debian11.sh --skip-daemon-mirror
```

## 5. 脚本实际部署内容

脚本内部会执行以下逻辑：

### 5.1 安装 Docker

- 安装依赖：`ca-certificates`、`curl`、`gnupg`、`lsb-release`
- 添加阿里云 Docker 软件源
- 安装：
  - `docker-ce`
  - `docker-ce-cli`
  - `containerd.io`
  - `docker-buildx-plugin`
  - `docker-compose-plugin`

### 5.2 配置 Docker 镜像加速

默认写入 `/etc/docker/daemon.json`：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io",
    "https://mirror.baidubce.com",
    "https://dockerproxy.com"
  ]
}
```

如果系统里已经存在 `/etc/docker/daemon.json`，脚本默认不会强制覆盖，只会提示你保留现有配置。

### 5.3 启动项目

脚本会调用项目自带：

```bash
docker compose -f docker/docker-compose.yml up -d --no-build
```

并通过环境变量指定镜像：

```bash
PING_MONITOR_IMAGE=tannic666/ping-monitor:v1.5.0
```

## 6. 默认容器与端口

脚本默认启动以下容器：

- `ping-monitor`
- `ping-monitor-mysql`
- `ping-monitor-redis`

默认映射端口：

- 应用：`8000`
- MySQL：`3307`
- Redis：`6379`

## 7. 常用运维命令

查看容器状态：

```bash
docker compose -f docker/docker-compose.yml ps
```

查看日志：

```bash
docker compose -f docker/docker-compose.yml logs -f --tail=200
```

重启服务：

```bash
docker compose -f docker/docker-compose.yml restart
```

停止服务：

```bash
docker compose -f docker/docker-compose.yml down
```

重新拉镜像并启动：

```bash
PING_MONITOR_IMAGE=tannic666/ping-monitor:latest docker compose -f docker/docker-compose.yml pull
PING_MONITOR_IMAGE=tannic666/ping-monitor:latest docker compose -f docker/docker-compose.yml up -d --no-build
```

## 8. 如何升级

如果你已经在服务器部署过这个项目，后续升级通常只需要：

```bash
cd /你的项目目录/ping-monitor
git pull
sudo bash scripts/deploy-docker-debian11.sh --deploy-only --image tannic666/ping-monitor:latest
```

如果你希望固定版本，则把 `latest` 改成具体版本号，例如：

```bash
sudo bash scripts/deploy-docker-debian11.sh --deploy-only --image tannic666/ping-monitor:v1.5.0
```

## 9. 常见问题

### 9.1 执行脚本时报权限不足

请使用 `root` 或 `sudo` 执行：

```bash
sudo bash scripts/deploy-docker-debian11.sh
```

### 9.2 执行后访问不到 8000

请检查：

- 云服务器安全组是否开放 `8000`
- 服务器本地防火墙是否放行 `8000`
- 容器是否启动成功：`docker compose -f docker/docker-compose.yml ps`

### 9.3 Docker 拉取镜像慢

可以先执行教程里的“替换 Debian 软件源”，并保留脚本自动写入的 Docker 镜像加速配置。

### 9.4 想完全手工部署

你也可以分两步执行：

1. 先安装 Docker
2. 再执行：

```bash
export PING_MONITOR_IMAGE=tannic666/ping-monitor:v1.5.0
docker compose -f docker/docker-compose.yml up -d --no-build
```

## 10. 相关文件

- 部署脚本：[scripts/deploy-docker-debian11.sh](../scripts/deploy-docker-debian11.sh)
- MySQL + Redis 说明：[docs/DEPLOYMENT_MYSQL_REDIS.md](./DEPLOYMENT_MYSQL_REDIS.md)
- 项目主页说明：[README.md](../README.md)
