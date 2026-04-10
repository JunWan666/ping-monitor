# MySQL + Redis 可选部署说明

## 1. 部署模式

当前项目支持两种模式：

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

- `ping_records` 达到 100 万级以上
- 希望提升日志查询、看板统计和聚合速度
- 需要可选缓存能力

启动方式：

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql-redis.yml up -d
```

## 2. 配置文件

建议先复制一份环境变量文件：

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

常用配置：

- `JWT_SECRET_KEY`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `ENABLE_CACHE`
- `CACHE_TTL_DASHBOARD`
- `CACHE_TTL_DATABOARD`
- `CACHE_TTL_HOST_DETAIL`

## 3. SQLite 与 MySQL 的选择逻辑

系统启动时规则如下：

- 如果设置了 `DATABASE_URL`，优先使用 `DATABASE_URL`
- 如果没有设置 `DATABASE_URL`，自动回退到 SQLite
- 如果没有设置 `REDIS_URL`，自动关闭 Redis 缓存

因此：

- 原有 SQLite 部署不受影响
- MySQL + Redis 只是增强模式，不是强依赖

## 4. 首次从 SQLite 迁移到 MySQL

如果你已有 SQLite 历史数据，可以执行迁移脚本：

```bash
python scripts/migrate_sqlite_to_mysql.py --mysql-url "mysql+pymysql://ping_monitor:CHANGE_ME_IN_DOT_ENV@127.0.0.1:3306/ping_monitor?charset=utf8mb4"
```

如果希望先清空 MySQL 目标表，再重新导入：

```bash
python scripts/migrate_sqlite_to_mysql.py --mysql-url "mysql+pymysql://ping_monitor:CHANGE_ME_IN_DOT_ENV@127.0.0.1:3306/ping_monitor?charset=utf8mb4" --truncate
```

默认 SQLite 路径为：

```text
data/ping_monitor.db
```

如需指定其他 SQLite 文件：

```bash
python scripts/migrate_sqlite_to_mysql.py --sqlite-path "data/your.db" --mysql-url "mysql+pymysql://ping_monitor:CHANGE_ME_IN_DOT_ENV@127.0.0.1:3306/ping_monitor?charset=utf8mb4"
```

## 5. Redis 作用说明

Redis 当前用于：

- 仪表盘缓存
- 数据看板缓存
- 单主机图表缓存

Redis 当前不作为：

- 历史 Ping 数据唯一存储
- 聚合统计唯一存储

真实数据仍然保存在 SQL 数据库中。

## 6. 常用命令

查看服务日志：

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

## 7. 验证是否生效

应用启动后访问根接口或登录系统后查看：

- 数据库是否为 MySQL
- 缓存是否启用

若未配置前端构建资源，后端根路径会返回 JSON 信息。

启用增强模式后，预期效果：

- 大日志表分页更稳定
- 仪表盘刷新更快
- 数据看板统计响应更快
- 配置修改后调度任务可热更新
