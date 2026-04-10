# Ping Monitor 架构优化方案

## 1. 方案目标

这份方案围绕一个核心原则展开：

- 保留当前 `SQLite` 模式，现有用户不需要改动也能继续使用。
- 增加 `MySQL` 作为可选关系型数据库后端，面向大数据量场景。
- 增加 `Redis` 作为可选加速层，用于缓存和热点数据提速。
- 不让 `MySQL` 和 `Redis` 变成强制依赖，不影响只想继续使用 `SQLite` 的部署方式。

目标架构如下：

- `SQLite`：默认模式，零额外服务，适合轻量部署
- `MySQL`：可选持久化数据库，适合 100 万级以上记录
- `Redis`：可选缓存层，提升仪表盘、统计页、热点查询性能

## 2. 当前项目现状评估

### 2.1 当前存储结构

当前项目所有业务数据都放在一个 SQLite 数据库里，主要表包括：

- `hosts`
- `ping_records`
- `alerts`
- `system_config`
- `users`
- `ping_statistics`
- `system_logs`

好消息是数据库入口比较集中，主要在 `backend/database.py`，说明数据库切换点比较明确，改造成本是可控的。

### 2.2 当前性能特点

当数据量较小时，当前结构是可用的。

但在 `ping_records` 达到 100 万级以上后，当前架构会逐渐暴露几个问题：

- `SQLite` 在多线程写入下并发能力偏弱。
- 多个接口会先把大量数据查出来，再放到 Python 内存里做筛选和聚合。
- 某些看板接口存在 N+1 查询问题。
- 聚合逻辑仍然比较依赖扫描原始历史数据。

所以现在的瓶颈并不只是“SQLite 不够快”，还包括：

- 查询方式本身偏重
- 分页和筛选没有完全下推到 SQL
- 缺少热点缓存
- 聚合任务仍然比较粗放

换成 MySQL 以后，这些问题仍然值得优化，只是 MySQL 能把瓶颈往后推很多。

## 3. 当前代码里的主要瓶颈

### 3.1 Ping 日志接口先全量查，再内存分页

`/api/ping/logs` 当前逻辑大致是：

- 先 `join` 主机和 Ping 记录
- 把所有满足条件的数据 `.all()` 查出来
- 在 Python 里判断正常/异常
- 再在 Python 里做分页

这在百万级表上是最明显的性能问题之一，对 `SQLite` 和 `MySQL` 都不友好。

### 3.2 仪表盘存在 N+1 查询

`/api/dashboard` 当前流程是：

- 先查所有主机
- 再对每台主机分别查一次最新 Ping 记录

主机数一多，就会产生很多额外 SQL 往返。

### 3.3 数据看板仍然有大量 Python 侧聚合

`/api/databoard/stats/{time_range}` 以及相关趋势接口里仍然存在较多：

- `.all()`
- Python 循环
- 每台主机逐个聚合

数据量和主机数一起来时，这一块会越来越重。

### 3.4 聚合任务仍然偏扫描式

`aggregate_hourly_stats()` 和 `aggregate_daily_stats()` 当前逻辑是：

- 按时间窗口循环
- 再按主机循环
- 每个窗口再查一遍原始数据

这种方式在历史数据大之后开销会明显上升。

### 3.5 配置项存在但没有完全生效

当前系统已经有这些配置项：

- `packet_count`
- `packet_timeout`
- `aggregate_interval`
- `cleanup_time`

但运行时部分逻辑还是写死值，所以配置系统的价值没有完全发挥出来。

## 4. 推荐的目标架构

### 4.1 持久化数据仍然放在 SQL 中

所有业务真实数据仍然建议保存在 SQL 数据库里，也就是：

- `SQLite` 或 `MySQL`

这些数据都应继续放在 SQL 中：

- 主机信息
- Ping 原始记录
- 告警记录
- 系统配置
- 用户信息
- 聚合统计
- 系统日志

### 4.2 Redis 不建议作为聚合历史的唯一存储

`Redis` 很适合做：

- 缓存
- 热点摘要
- 短时计算结果
- 未来多实例下的分布式锁

但不建议一开始就让 Redis 成为历史聚合数据的唯一存储。

推荐原则：

- SQL 是真实数据源
- Redis 存放热点 API 的缓存结果

这样既能提速，又不会增加数据丢失和恢复复杂度。

### 4.3 兼容策略

应用应根据配置自动选择后端：

- 没有 `DATABASE_URL`：走当前 SQLite 模式
- 有 `DATABASE_URL` 且是 MySQL：走 MySQL 模式
- 没有 `REDIS_URL`：Redis 功能自动关闭
- 有 `REDIS_URL`：启用缓存能力

这样可以保证旧部署完全不受影响。

## 5. 推荐的升级设计

### 第一阶段：先实现可选后端，不破坏 SQLite

#### 5.1 数据库配置模型

建议把当前“只支持 SQLite 文件路径”的逻辑改成：

- 优先读取 `DATABASE_URL`
- 如果没有，则回退到当前 `DB_PATH` / SQLite 逻辑

推荐形式：

- SQLite：
  - `sqlite:///data/ping_monitor.db`
- MySQL：
  - `mysql+pymysql://ping_monitor:CHANGE_ME_IN_DOT_ENV@mysql:3306/ping_monitor?charset=utf8mb4`

#### 5.2 数据库引擎初始化

数据库引擎要按不同方言做不同配置：

- `SQLite`
  - 保留 `check_same_thread=False`
- `MySQL`
  - 增加 `pool_pre_ping=True`
  - 增加连接池大小、回收超时等参数

#### 5.3 保留当前 compose 默认方案

不要直接替换现在的 `docker/docker-compose.yml`。

建议：

- 保留它作为 SQLite 默认部署文件
- 新增一个增强版 overlay 文件，例如：
  - `docker/docker-compose.mysql-redis.yml`

推荐启动方式：

- 仅 SQLite：
  - `docker compose -f docker/docker-compose.yml up -d`
- MySQL + Redis：
  - `docker compose -f docker/docker-compose.yml -f docker/docker-compose.mysql-redis.yml up -d`

这是兼容旧用户最稳妥的方式。

### 第二阶段：优先优化 SQL 查询路径

这一阶段对 `SQLite` 和 `MySQL` 都有价值。

#### 5.4 重写 `/api/ping/logs`

目标：

- 把正常/异常筛选下推到 SQL
- 直接用 SQL 分页
- 不再 `.all()` 后再分页
- 总数用 SQL `count` 获取

预期收益：

- 百万级数据查询压力明显下降
- Python 内存占用显著降低

#### 5.5 重写 `/api/dashboard`

把“每台主机查一次最新记录”的逻辑改成：

- 子查询取每台主机最新时间
- 再关联取最新记录

预期收益：

- 消除 N+1
- 仪表盘随主机数量增长时更稳定

#### 5.6 优化数据看板接口

长时间范围统计应尽量：

- 优先使用 `ping_statistics`
- 让更多聚合在 SQL 层完成
- 降低 Python 层循环

短时间范围则应：

- 明确限制查询窗口
- 限制结果数量

#### 5.7 优化聚合任务

小时聚合、天聚合应尽量改成：

- SQL `group by`
- 批量生成统计

而不是继续采用：

- 时间段循环
- 主机循环
- 每段都查原始明细

预期收益：

- 聚合任务耗时明显下降
- 调度任务在大数据量下更稳定

### 第三阶段：补上真正匹配查询模式的索引

这一步无论是否切到 MySQL，都建议做。

推荐新增或强化的索引：

- `ping_records(host_id, created_at)`
- `ping_records(created_at)`
- `alerts(created_at)`
- `alerts(host_id, created_at)`
- `ping_statistics(host_id, stat_type, stat_time)`
- `system_logs(created_at)`
- `system_logs(log_type, created_at)`
- `system_logs(module, created_at)`

说明：

- 当前模型里已经有一些单列索引
- 但在百万级数据下，复合索引比单列索引更关键

### 第四阶段：增加可选 Redis 缓存层

Redis 应该作为“纯可选增强层”加入。

#### 5.8 推荐优先缓存的接口

优先缓存：

- 仪表盘摘要
- 仪表盘主机状态列表
- 数据看板总体统计
- 数据看板趋势数据
- 单主机详情图表

不建议优先缓存：

- 登录鉴权
- 高频变化的原始 Ping 日志列表

#### 5.9 推荐 TTL

建议缓存时间：

- 仪表盘摘要：10 到 15 秒
- 数据看板统计：30 到 60 秒
- 单主机详情图表：30 秒

这类 TTL 足够短，基本不会影响使用感知，同时也足够长，能显著减轻数据库压力。

#### 5.10 缓存失效时机

以下事件发生时，应清理相关缓存：

- 手动 Ping 完成
- 一轮定时监控完成
- 主机配置修改
- 数据清理完成
- 小时聚合或天聚合完成

#### 5.11 可选的热点状态缓存

Redis 很适合额外保存每台主机的最新状态，例如：

- 最新丢包率
- 最新平均延迟
- 最新检测时间
- 最新状态

这样仪表盘可以优先读 Redis，速度会更快，但 SQL 仍然是最终真实来源。

### 第五阶段：迁移和结构演进

#### 5.12 保持一套 SQLAlchemy 模型

不建议拆成：

- SQLite 一套模型
- MySQL 一套模型

建议继续保持：

- 一套 SQLAlchemy 模型
- 一层数据库后端选择逻辑

这样后续维护最简单。

#### 5.13 弱化 SQLite 专用迁移方式

当前迁移逻辑比较轻量，且偏向 SQLite。

为了未来同时支持 `SQLite + MySQL`，更好的方向是：

- 短期：当前轻量迁移逻辑继续保留给 SQLite
- 中期：引入 Alembic 做正式迁移管理

一旦上 MySQL，这一步的重要性会提高很多。

#### 5.14 历史数据迁移路径

如果已经积累了 SQLite 历史数据，推荐迁移步骤：

1. 从 SQLite 导出
2. 建立 MySQL 结构
3. 导入历史数据
4. 校验记录数
5. 切换 `DATABASE_URL`

这部分最好提供成专门脚本，而不是手工迁移。

## 6. Redis 的边界建议

为了保持系统稳定，Redis 在第一轮最好控制在以下范围：

推荐：

- 只做缓存
- 只做热点状态
- 未来如果有多实例部署，再增加分布式锁

第一轮不建议：

- 把 Redis 变成强依赖
- 只把聚合结果存 Redis
- 一开始就把调度系统改造成 Redis 队列

那样会明显增加系统复杂度。

## 7. 建议的配置模型

推荐环境变量：

- `DATABASE_URL`
- `DB_PATH`
- `REDIS_URL`
- `ENABLE_CACHE`
- `CACHE_TTL_DASHBOARD`
- `CACHE_TTL_DATABOARD`

推荐回退规则：

- `DATABASE_URL` 不存在 -> 走 `DB_PATH` / SQLite
- `REDIS_URL` 不存在 -> 自动关闭缓存
- `ENABLE_CACHE=false` -> 即使配了 Redis 也不启用缓存

## 8. 部署策略

### 8.1 保持当前部署不变

现有部署方式应继续适用于：

- 本地 SQLite 开发
- 简单 Docker SQLite 部署

### 8.2 新增增强版部署

新增一个可选 compose 文件，提供：

- MySQL
- Redis
- 应用环境变量注入

这样用户就可以自己选择：

- 简单模式
- 增强模式

而不是被迫升级整套部署方式。

## 9. 推荐实施顺序

### Step A：兼容基础层

- 增加 `DATABASE_URL` 支持
- 增加 `REDIS_URL` 支持
- 保留 SQLite 回退

### Step B：查询优化

- 优化 `/api/ping/logs`
- 优化 `/api/dashboard`
- 优化数据看板查询

### Step C：索引优化

- 增加复合索引
- 验证慢查询路径

### Step D：Redis 缓存

- 给仪表盘、数据看板加缓存
- 增加缓存失效钩子

### Step E：部署与迁移

- 增加新的 compose overlay
- 增加 `.env.example`
- 增加 SQLite -> MySQL 迁移说明或脚本

## 10. 难度评估

总体难度：中等。

拆分来看：

- 可选 `SQLite/MySQL` 支持：中等
- 可选 `Redis` 缓存层：低到中等
- 查询重构优化：中等
- 迁移脚本与部署增强：中等

真正最难的部分不是“接上 MySQL 和 Redis”，而是把重查询路径真正改成能扛数据量的结构。

## 11. 实际建议

对于这个项目，最稳妥的路径是：

1. 不要一上来就把 Redis 当聚合主存储。
2. 先把 SQL 持久层做成可选。
3. 先优化真正重的查询路径。
4. 再把 Redis 作为可选加速层接进去。

这样做的好处是：

- 扩展性更强
- 迁移风险更低
- 对原有 SQLite 用户零破坏
- Docker 部署路径更清晰

## 12. 当前仓库最值得优先做的改动

最高优先级建议：

- 支持 `DATABASE_URL`，并保留 SQLite 回退
- 支持可选 `REDIS_URL`
- 优化 `/api/ping/logs`
- 优化 `/api/dashboard`
- 优化聚合任务
- 增加复合索引
- 新增 `docker/docker-compose.mysql-redis.yml`

这些改动在“不打破现有 SQLite”的前提下，能带来最大的收益。
