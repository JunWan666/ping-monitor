# MySQL + Redis 部署说明

## 1. 部署模式

当前项目支持两种运行模式：

### 模式一：默认 SQLite

适合：

- 小规模部署
- 本地测试
- 不想额外维护 MySQL / Redis

启动方式：

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 模式二：增强版 MySQL + Redis

适合：

- `ping_records` 已达到百万级
- 希望提升日志查询、仪表盘统计、聚合接口响应速度
- 需要使用缓存减轻数据库压力

启动方式：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql-redis.yml up -d
```

## 2. 环境变量

建议先复制一份环境变量文件：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

常用配置：

- `JWT_SECRET_KEY`
- `MYSQL_BIND_HOST`
- `MYSQL_PORT`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `REDIS_BIND_HOST`
- `REDIS_PORT`
- `REDIS_PASSWORD`
- `ENABLE_CACHE`
- `CACHE_TTL_DASHBOARD`
- `CACHE_TTL_DATABOARD`
- `CACHE_TTL_HOST_DETAIL`

## 3. 数据库与缓存选择逻辑

系统启动时遵循以下规则：

- 如果设置了 `DATABASE_URL`，优先使用 `DATABASE_URL`
- 如果没有设置 `DATABASE_URL`，自动回退到 SQLite
- 如果没有设置 `REDIS_URL`，自动关闭 Redis 缓存

这意味着：

- 原有 SQLite 部署不会被破坏
- MySQL + Redis 是增强模式，不是强依赖

## 4. 默认端口策略

从当前版本开始，`MySQL` 和 `Redis` 默认会同时具备两层访问能力：

- 应用容器通过 `mysql:3306` 访问 MySQL
- 应用容器通过 `redis:6379` 访问 Redis
- 宿主机默认把 MySQL 绑定到 `127.0.0.1:${MYSQL_PORT:-3307}`
- 宿主机默认把 Redis 绑定到 `127.0.0.1:${REDIS_PORT:-6380}`

这样做的好处：

- 不会和宿主机已有的 `3306` / `6379` 冲突
- 默认只能在服务器本机访问，更安全
- 仍然支持通过 SSH 隧道远程查看数据库 / Redis
- 对当前项目功能没有影响

如果你确实需要让外部机器直接访问：

- 把 `MYSQL_BIND_HOST` 改成 `0.0.0.0`
- 把 `REDIS_BIND_HOST` 改成 `0.0.0.0`
- 保持密码已修改
- 再额外配置防火墙，只允许你的办公 IP 访问

默认情况下不建议直接把数据库和 Redis 暴露到公网。

## 4.1 默认安全配置示例

`.env` 示例：

```dotenv
MYSQL_BIND_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_ROOT_PASSWORD=CHANGE_ME_IN_DOT_ENV
MYSQL_DATABASE=ping_monitor
MYSQL_USER=ping_monitor
MYSQL_PASSWORD=CHANGE_ME_IN_DOT_ENV

REDIS_BIND_HOST=127.0.0.1
REDIS_PORT=6380
REDIS_PASSWORD=CHANGE_ME_IN_DOT_ENV
```

在这个配置下：

- 应用容器内部仍然正常通过 `mysql:3306` 和 `redis:6379` 通信
- 宿主机可以通过 `127.0.0.1:3307` 访问 MySQL
- 宿主机可以通过 `127.0.0.1:6380` 访问 Redis
- 外部机器不能直接访问，更适合生产环境

## 4.2 推荐远程查看方式：SSH 隧道

如果你想从自己电脑远程查看数据库，推荐走 SSH 隧道，而不是直接开放公网端口。

MySQL：

```bash
ssh -L 3307:127.0.0.1:3307 root@你的服务器IP
```

连接参数：

- Host: `127.0.0.1`
- Port: `3307`
- User: `ping_monitor`
- Password: `.env` 中的 `MYSQL_PASSWORD`
- Database: `ping_monitor`

Redis：

```bash
ssh -L 6380:127.0.0.1:6380 root@你的服务器IP
```

测试命令：

```bash
redis-cli -h 127.0.0.1 -p 6380 -a "你的REDIS_PASSWORD" ping
```

## 4.3 如需公网直连

如果你确认要让其他机器直接连服务器上的 MySQL / Redis：

```dotenv
MYSQL_BIND_HOST=0.0.0.0
REDIS_BIND_HOST=0.0.0.0
```

然后重启这套 compose。这样做以后，请务必：

- 修改默认密码
- 配置云防火墙 / `ufw` / 安全组白名单
- 不要开放给整个公网

## 5. 首次从 SQLite 迁移到 MySQL

### 推荐方式：使用更新脚本自动迁移

```bash
./scripts/update-latest.sh --mode mysql-redis --migrate-sqlite --truncate-mysql
```

说明：

- `--migrate-sqlite` 会把 `data/ping_monitor.db` 迁移到 MySQL
- `--truncate-mysql` 会在导入前清空目标表，适合首次迁移或重导

### 手动方式：在应用容器内执行迁移

因为默认不对宿主机暴露 MySQL 端口，手动迁移建议在容器内部执行：

```bash
docker exec ping-monitor python /app/scripts/migrate_sqlite_to_mysql.py \
  --sqlite-path data/ping_monitor.db \
  --mysql-url "mysql+pymysql://ping_monitor:CHANGE_ME_IN_DOT_ENV@mysql:3306/ping_monitor?charset=utf8mb4" \
  --batch-size 5000 \
  --rebuild-statistics
```

如果需要先清空 MySQL 再导入：

```bash
docker exec ping-monitor python /app/scripts/migrate_sqlite_to_mysql.py \
  --sqlite-path data/ping_monitor.db \
  --mysql-url "mysql+pymysql://ping_monitor:CHANGE_ME_IN_DOT_ENV@mysql:3306/ping_monitor?charset=utf8mb4" \
  --batch-size 5000 \
  --rebuild-statistics \
  --truncate
```

默认 SQLite 路径：

```text
data/ping_monitor.db
```

如果你的 SQLite 文件不在默认位置，可以自行替换 `--sqlite-path`。

## 6. Redis 的作用

Redis 当前主要用于：

- 仪表盘缓存
- 数据看板缓存
- 单主机趋势图缓存

Redis 当前不是：

- 历史 Ping 明细的唯一存储
- 聚合统计的唯一存储

真实业务数据仍然保存在 SQL 数据库中。

Redis 在当前版本已支持密码保护：

- 应用容器内部自动使用 `REDIS_PASSWORD` 连接
- 宿主机或远程调试时，请使用 `redis-cli -a "你的REDIS_PASSWORD"`

## 7. 常用命令

查看服务状态：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql-redis.yml ps
```

查看日志：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql-redis.yml logs -f
```

停止服务：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql-redis.yml down
```

重建并启动：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql-redis.yml up -d --build
```

仅查看 MySQL：

```bash
docker exec -it ping-monitor-mysql mysql -u"${MYSQL_USER:-ping_monitor}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE:-ping_monitor}"
```

仅查看 Redis：

```bash
docker exec -it ping-monitor-redis sh -lc 'redis-cli -a "$REDIS_PASSWORD"'
```

## 8. 如何确认已经生效

部署完成后，可以从这些角度确认：

- `docker ps` 中 `ping-monitor-mysql` 和 `ping-monitor-redis` 正常运行
- `docker exec ping-monitor sh -lc 'getent hosts mysql && getent hosts redis'` 可以解析
- 应用页面里的数据库状态显示为 MySQL
- 仪表盘、数据看板、趋势接口响应时间明显下降
- 重启容器后数据仍然存在，说明 MySQL / Redis 卷已经生效

如果页面仍然卡顿，优先继续检查：

- 是否已经完成 SQLite 到 MySQL 的数据迁移
- 是否仍在读取旧 SQLite 文件
- 聚合任务是否执行成功
- Redis 缓存是否启用
