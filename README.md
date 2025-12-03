# Ping监控系统

一个基于 FastAPI + Vue3 + Element Plus 的网络主机监控系统，支持自动化 Ping 检测、告警通知和数据可视化。

## 1. 功能特性

### 1.1 核心功能
- 🔍 **主机监控** - 支持添加多个主机，实时监控网络状态
- 📊 **数据可视化** - 使用 ECharts 展示延迟和丢包率趋势
- 🔔 **告警通知** - 支持 Server酱 和 Webhook（钉钉）通知
- ⏰ **定时检测** - 自动按设定间隔执行 Ping 检测
- 📝 **日志记录** - 完整的 Ping 日志记录和查询
- ⚙️ **灵活配置** - 可自定义检测间隔、超时时间、告警阈值等
- 🔐 **用户认证** - 基于JWT的登录认证系统，支持管理员账户管理
- 🔍 **搜索筛选** - 支持主机名称/地址模糊搜索，状态筛选
- 📄 **分页功能** - 列表数据支持分页显示，提升浏览体验

### 1.2 界面功能
- **登录页面** - 管理员账户登录，首次使用需初始化管理员
- **仪表盘** - 查看所有主机的实时状态和统计信息，支持搜索和状态筛选
- **主机管理** - 添加、编辑、删除监控主机，支持手动 Ping 和 Excel 导入/导出，支持搜索筛选和分页
- **数据看板** - 查看不同时间范围的统计数据，支持整体趋势和分主机统计
- **告警记录** - 查看历史告警信息，支持分页查询和时间范围筛选
- **系统设置** - 配置检测参数、数据维护和通知方式，支持通知模式设置
- **Ping日志** - 查看详细的 Ping 检测记录，支持分页和状态筛选
- **系统日志** - 查看系统自动操作记录，支持手动触发数据维护任务
- **修改密码** - 支持修改用户名和密码，需验证原密码

## 2. 技术栈

### 2.1 后端
- **FastAPI** - 现代化的 Python Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **SQLite** - 轻量级数据库
- **APScheduler** - 定时任务调度
- **ping3** - Python Ping 实现
- **python-jose** - JWT 令牌处理
- **passlib** - 密码加密

### 2.2 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Element Plus** - Vue 3 组件库
- **ECharts** - 数据可视化图表
- **Axios** - HTTP 客户端
- **Vite** - 现代化构建工具

## 3. 项目结构

```
ping-monitor/
├── backend/                  # 后端目录
│   ├── main.py              # FastAPI 主程序和 API 路由
│   ├── database.py          # 数据库模型定义
│   ├── database_migrations.py  # 数据库迁移模块（自动同步表结构）
│   ├── ping_service.py      # Ping 检测服务
│   ├── scheduler.py         # 定时任务调度器
│   ├── data_maintenance.py  # 数据维护模块（清理和聚合）
│   ├── notification.py      # 通知服务（Server酱/Webhook）
│   ├── notification_template.py  # 通知消息模板（Markdown格式）
│   ├── auth.py              # JWT认证和密码加密
│   └── requirements.txt     # Python 依赖
│
├── frontend/                # 前端目录
│   ├── src/
│   │   ├── components/      # Vue 组件
│   │   │   ├── Dashboard.vue      # 仪表盘
│   │   │   ├── HostManage.vue     # 主机管理
│   │   │   ├── AlertList.vue      # 告警记录
│   │   │   ├── DataBoard.vue      # 数据看板
│   │   │   ├── Settings.vue       # 系统设置
│   │   │   ├── SystemLogs.vue     # 系统日志
│   │   │   ├── Login.vue          # 登录页面
│   │   │   ├── InitAdmin.vue      # 管理员初始化
│   │   │   ├── UserProfile.vue    # 用户信息修改
│   │   │   └── Main.vue           # 主框架
│   │   ├── App.vue          # 主应用组件
│   │   ├── api.js           # API 接口封装
│   │   ├── router.js        # 路由配置
│   │   └── main.js          # 入口文件
│   ├── package.json         # Node 依赖
│   └── vite.config.js       # Vite 配置
│
├── docker/                  # Docker 相关文件
│   ├── Dockerfile           # Docker 镜像构建文件
│   ├── docker-compose.yml   # Docker Compose 配置
│   ├── .dockerignore        # Docker 构建忽略文件
│   ├── docker-start.bat     # Windows 一键启动脚本
│   └── README.md            # Docker 部署说明
│
├── docs/                    # 文档目录
│   └── LOGIN_README.md      # 登录认证系统说明
│
├── data/                    # 数据目录（运行后生成）
│   └── ping_monitor.db      # SQLite 数据库文件
│
├── migrate_db_docker.py     # Docker环境数据库迁移脚本
├── migrate_db_docker.sh     # Docker数据库迁移执行脚本
├── .gitignore               # Git 忽略文件
├── LICENSE                  # MIT 开源协议
├── start.bat                # Windows 一键启动脚本
└── README.md                # 项目说明文档
```

## 4. 快速开始

### 4.1 方法一：Docker 部署（推荐）

#### 4.1.1 直接使用镜像（无需构建）

**Windows (PowerShell):**
```powershell
docker run -d --name ping-monitor -p 8000:8000 -v "$PWD/data:/app/data" -e TZ=Asia/Shanghai --restart unless-stopped tannic666/ping-monitor:latest
```

**Windows (CMD):**
```cmd
docker run -d --name ping-monitor -p 8000:8000 -v "%cd%/data:/app/data" -e TZ=Asia/Shanghai --restart unless-stopped tannic666/ping-monitor:latest
```

**Linux / macOS:**
```bash
docker run -d --name ping-monitor -p 8000:8000 -v "$(pwd)/data:/app/data" -e TZ=Asia/Shanghai --restart unless-stopped tannic666/ping-monitor:latest
```

#### 4.1.2 本地构建镜像

**Windows (PowerShell):**
```powershell
# 构建镜像
docker build -f docker/Dockerfile -t ping-monitor .

# 运行容器
docker run -d --name ping-monitor -p 8000:8000 -v "$PWD/data:/app/data" -e TZ=Asia/Shanghai --restart unless-stopped ping-monitor
```

**Windows (CMD):**
```cmd
# 构建镜像
docker build -f docker/Dockerfile -t ping-monitor .

# 运行容器
docker run -d --name ping-monitor -p 8000:8000 -v "%cd%/data:/app/data" -e TZ=Asia/Shanghai --restart unless-stopped ping-monitor
```

**Linux / macOS:**
```bash
# 构建镜像
docker build -f docker/Dockerfile -t ping-monitor .

# 运行容器
docker run -d --name ping-monitor -p 8000:8000 -v "$(pwd)/data:/app/data" -e TZ=Asia/Shanghai --restart unless-stopped ping-monitor
```

#### 4.1.3 使用 docker-compose（推荐）

```bash
# 进入docker目录
cd docker

# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重新构建并启动
docker-compose up -d --build
```

#### 4.1.4 Docker 常用命令

```bash
# 查看日志
docker logs -f ping-monitor

# 停止容器
docker stop ping-monitor

# 启动容器
docker start ping-monitor

# 删除容器
docker rm -f ping-monitor
```

访问地址：http://localhost:8000

### 4.2 方法二：本地开发环境

#### 4.2.1 环境要求
- Python 3.8+
- Node.js 20+
- Windows/Linux/macOS

#### 4.2.2 一键启动（Windows）
```bash
# 双击运行 start.bat 文件，自动安装依赖并启动服务
start.bat
```

#### 4.2.3 手动启动

**1. 安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

**2. 启动后端服务**
```bash
python main.py
```
后端服务运行在：http://localhost:8000

**3. 安装前端依赖**
```bash
cd frontend
npm install
```

**4. 启动前端服务**
```bash
npm run dev
```
前端服务运行在：http://localhost:5173

#### 4.2.4 访问系统

**首次访问**
- 系统会自动跳转到管理员初始化页面
- 设置管理员用户名和密码（密码至少5位）
- 初始化完成后自动跳转到登录页面

**后续访问**
- **Docker 部署**：http://localhost:8000
- **开发环境**：
  - 前端界面：http://localhost:5173
  - API 文档：http://localhost:8000/docs
  - API 接口：http://localhost:8000/api

## 5. 使用说明

### 5.1 添加监控主机
1. 进入「主机管理」页面
2. 点击「添加主机」按钮
3. 填写主机信息：
   - **主机名称**：便于识别的名称
   - **主机地址**：IP 地址或域名
   - **描述**：可选的说明信息
   - **告警阈值**：丢包率超过此值时触发告警（默认 20%）
4. 点击「确定」保存

### 5.2 配置系统参数
1. 进入「系统设置 - 基本设置」
2. 配置检测参数：
   - **检测间隔**：自动检测的时间间隔（分钟）
   - **发送包数**：每次 Ping 发送的数据包数量
   - **超时时间**：Ping 超时时间（秒）
3. 配置通知方式（可选）：
   - **Server酱密钥**：填写 Server酱的 SendKey
   - **Webhook 地址**：填写钉钉机器人的 Webhook 地址
   - **Webhook 加签密钥**：填写钉钉机器人的加签密钥
4. 点击「保存配置」

### 5.3 查看监控数据
- **仪表盘**：查看所有主机的实时状态、延迟、丢包率
- **告警记录**：查看触发的告警信息
- **Ping日志**：查看详细的检测记录，支持按主机筛选和分页

### 5.4 手动执行 Ping
1. 在「主机管理」页面，点击主机操作栏的「Ping」按钮
2. 系统会立即执行 Ping 检测并显示结果
3. 检测过程中可以点击「取消」按钮中断操作

### 5.5 批量导入主机
1. 在「主机管理」页面，点击「导入主机」
2. 选择 Excel 文件（支持 .xlsx 格式）
3. Excel 表格需包含列：主机名称、主机地址、描述、告警阈值
4. 系统会自动导入并创建主机

### 5.6 导出主机列表
1. 在「主机管理」页面，点击「导出主机」
2. 系统会生成 Excel 文件并自动下载
3. 文件包含所有主机的完整信息

## 6. API 接口

### 6.1 主机管理
- `GET /api/hosts` - 获取所有主机
- `POST /api/hosts` - 添加主机
- `GET /api/hosts/{id}` - 获取单个主机
- `PUT /api/hosts/{id}` - 更新主机
- `DELETE /api/hosts/{id}` - 删除主机

### 6.2 Ping 操作
- `POST /api/ping/{id}` - 立即执行 Ping
- `GET /api/ping/logs` - 获取 Ping 日志（支持分页和筛选）

### 6.3 监控数据
- `GET /api/dashboard` - 获取仪表盘数据
- `GET /api/records/{id}` - 获取主机监控记录
- `GET /api/alerts` - 获取告警记录

### 6.4 数据看板
- `GET /api/databoard/stats/{timeRange}` - 获取数据看板统计（timeRange: 1h/1d/3d/7d/15d/30d）
- `GET /api/databoard/host/{hostId}/{timeRange}` - 获取单个主机详细统计

### 6.5 系统配置
- `GET /api/config` - 获取系统配置
- `PUT /api/config` - 更新系统配置
- `POST /api/test-notification/{type}` - 测试通知功能

### 6.6 系统日志
- `GET /api/system-logs` - 获取系统日志（支持分页和筛选）
- `POST /api/system-logs/cleanup` - 清理旧系统日志

### 6.7 数据维护
- `POST /api/data-maintenance/aggregate-hourly` - 手动触发小时级聚合
- `POST /api/data-maintenance/aggregate-daily` - 手动触发日级聚合
- `POST /api/data-maintenance/cleanup` - 手动触发数据清理

详细的 API 文档请访问：http://localhost:8000/docs

## 7. 数据库结构

### 7.1 hosts（主机表）
- `id` - 主机 ID
- `name` - 主机名称（唯一）
- `address` - IP 地址或域名
- `description` - 描述信息
- `enabled` - 是否启用监控
- `alert_threshold` - 告警阈值（丢包率 %）
- `last_status` - 上次状态（normal/abnormal/unknown）
- `created_at` - 创建时间

### 7.2 ping_records（Ping 记录表）
- `id` - 记录 ID
- `host_id` - 关联主机 ID
- `packet_sent` - 发送包数
- `packet_received` - 接收包数
- `packet_loss` - 丢包率（%）
- `min_rtt` - 最小延迟（ms）
- `max_rtt` - 最大延迟（ms）
- `avg_rtt` - 平均延迟（ms）
- `created_at` - 检测时间

### 7.3 alerts（告警表）
- `id` - 告警 ID
- `host_id` - 关联主机 ID
- `host_name` - 主机名称
- `alert_type` - 告警类型
- `message` - 告警消息
- `is_sent` - 是否已发送通知
- `created_at` - 告警时间

### 7.4 system_config（系统配置表）
- `id` - 配置 ID
- `check_interval` - 检测间隔（分钟）
- `packet_count` - 发送包数
- `packet_timeout` - 超时时间（秒）
- `serverchan_key` - Server酱密钥
- `webhook_url` - Webhook 地址
- `webhook_secret` - Webhook 加签密钥
- `notification_mode` - 通知模式（status_change/every_time）
- `data_retention_days` - 原始数据保留天数（默认30）
- `cleanup_time` - 数据清理时间（默认03:00）
- `aggregate_interval` - 数据聚合间隔（默认1小时）
- `dashboard_chart_points` - 仪表盘趋势图显示的检测次数（默认12）
- `updated_at` - 更新时间

### 7.5 users（用户表）
- `id` - 用户 ID
- `username` - 用户名（唯一）
- `password_hash` - 加密后的密码
- `is_admin` - 是否管理员
- `created_at` - 创建时间

### 7.6 ping_statistics（数据聚合表）
- `id` - 统计 ID
- `host_id` - 关联主机 ID
- `stat_type` - 统计类型（hourly/daily）
- `stat_time` - 统计时间点
- `check_count` - 检测次数
- `online_count` - 在线次数
- `avg_packet_loss` - 平均丢包率（%）
- `avg_rtt` - 平均延迟（ms）
- `min_rtt` - 最小延迟（ms）
- `max_rtt` - 最大延迟（ms）
- `created_at` - 创建时间

### 7.7 system_logs（系统日志表）
- `id` - 日志 ID
- `log_type` - 日志类型（info/warning/error/cleanup/aggregate）
- `module` - 模块名称
- `message` - 日志内容
- `details` - 详细信息（JSON格式）
- `created_at` - 创建时间

## 8. 通知配置

### 8.1 Server酱
1. 访问 [Server酱官网](https://sct.ftqq.com/) 注册账号
2. 获取 SendKey
3. 在系统设置中填入 SendKey
4. 点击「测试通知」验证配置

### 8.2 钉钉机器人
1. 在钉钉群中添加自定义机器人
2. 获取 Webhook 地址和加签密钥
3. 在系统设置中填入配置
4. 点击「测试通知」验证配置

## 9. 常见问题

### Q: 从 v1.1.0 升级到 v1.2.0 需要数据库迁移吗？
A: 是的，v1.2.0 新增了数据库字段。如果你使用 Docker 部署：
```bash
# 方法1：直接执行迁移脚本
docker exec <容器名称> python /app/migrate_db_docker.py

# 方法2：使用Shell脚本
./migrate_db_docker.sh <容器名称>
```
如果是本地开发环境，直接重启后端服务即可自动创建新字段。

### Q: 后端启动失败，提示 “需要管理员权限”
A: 这是因为使用 `ping3` 库需要 ICMP 权限。解决方案：
- Windows：以管理员身份运行
- Linux/Mac：使用 `sudo` 运行或配置 `ping3` 权限

### Q: 前端无法连接后端
A: 检查以下几点：
1. 确认后端服务正在运行（http://localhost:8000）
2. 检查防火墙设置
3. 查看浏览器控制台的错误信息

### Q: Ping 检测不准确
A: 可以在系统设置中调整：
- 增加「发送包数」提高准确性
- 调整「超时时间」适应网络环境

### Q: 通知发送失败
A: 请检查：
1. Server酱密钥或 Webhook 地址是否正确
2. 网络是否可以访问通知服务
3. 使用「测试通知」功能验证配置

## 10. 开发说明

### 10.1 后端开发
```bash
cd backend
# 开发模式运行（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 10.2 前端开发
```bash
cd frontend
# 开发模式运行（热更新）
npm run dev

# 构建生产版本
npm run build
```

### 10.3 添加新功能
1. 后端：在 `main.py` 中添加 API 路由
2. 前端：在 `components/` 中创建 Vue 组件
3. 数据库：在 `database.py` 中修改模型定义

## 11. 更新日志

### v1.4.0 (2025-12-03)
#### 🔧 数据库自动迁移系统
- ✨ 新增 `database_migrations.py` 模块，实现数据库表结构自动同步
- 🔄 启动时自动检测 Model 定义和数据库实际结构的差异
- ✅ 自动添加缺失的数据库字段，无需手动执行 SQL
- 🛡️ 幂等性设计，重复执行不会出错，不破坏现有数据
- 📝 详细的迁移日志记录，清晰展示每次迁移操作
- 🚀 支持手动运行：`python database_migrations.py`

#### 📊 仪表盘体验优化
- ⚙️ 新增“仪表盘数据点”配置项，可自定义趋势图显示的检测次数（2-50次）
- 📈 监控数据趋势图动态计算加载数据量：主机数量 × 配置的检测次数
- 🎯 自适应多主机环境，确保显示足够的时间范围
- 📉 支持查看 10 分钟至数小时的趋势数据，灵活配置

#### 🐛 Bug修复与优化
- 🟢 系统日志消息颜色区分：小时级聚合（蓝色）、日级聚合（橙色加粗）、数据清理（绿色）
- ✅ 移除告警记录中的 ✅ 等状态符号，保持消息清晰简洁
- 🔍 Ping日志主机选择改为输入框模糊搜索，支持搜索主机名称和地址
- 🐛 修复前端过滤导致的“接口返回20条只显示1条”问题
- 📝 为“超时时间”配置添加详细说明，提升用户理解
- 🔢 系统日志序号列改为 ID 列，按 ID 降序显示，最新日志在前

#### 🚀 性能优化
- ⚡ 数据看板性能大幅提升：修复 N+1 查询问题，使用主机字典缓存
- 📊 扩大聚合数据使用范围：1天/3天也使用 hourly 聚合数据
- 📈 单个主机详情接口也使用聚合数据提升响应速度
- 🎯 性能提升 5-18 倍，查看历史数据更加流畅

#### 🎨 UI/UX 优化
- 📊 仪表盘监控数据趋势图添加在线率曲线（绿色）
- ✅ 在线率计算规则：丢包率 < 10% 算在线
- 🔧 通知配置逻辑优化：前端保留配置值，切换平台时无需重新输入

#### 💾 数据库更新
- 🆕 `system_config` 表新增字段：
  - `dashboard_chart_points` - 仪表盘趋势图显示的检测次数（默认 12）
- 🔄 **重要**：升级后自动执行数据库迁移，无需手动操作

### v1.3.0 (2025-12-01)
#### 📊 数据看板功能
- ✨ 新增数据看板页面，支持查看不同时间范围的统计数据
- 🕒 支持 6 种时间范围选择：过1小时、1天、3天、7天、15天、30天
- 📊 显示整体趋势图：在线主机数、平均丢包率、平均延迟
- 📊 分主机统计表格：监控次数、在线次数、在线率、平均丢包率、平均延迟
- 🔍 支持查看单个主机的详细趋势图（弹窗显示）
- 🎨 趋势图放在主机统计表格上方，布局更清晰
- 📊 表格列动态占满宽度，充分利用空间

#### 🛠️ 数据维护功能
- 🗄️ 新增数据聚合功能，支持小时级和日级数据聚合
- 🗑️ 新增自动数据清理，保留最近 30 天原始数据（可配置）
- 💾 聚合数据永久保留，提供历史数据查询能力
- ⏰ 定时任务自动执行：每小时聚合数据 + 每天凌晨3点清理旧数据（可配置）
- 📊 新增 `PingStatistics` 表存储聚合数据
- 📝 新增 `SystemLog` 表记录系统自动操作日志

#### 📋 系统日志功能
- 📝 新增系统日志菜单，集中查看系统自动操作记录
- 🔍 支持按日志类型、模块筛选查询
- 📊 分页显示（每靓50条），支持查看详细信息
- 🗑️ 支持清理30天前的旧日志
- 🔨 新增数据维护操作按钮：
  - 执行小时级聚合
  - 执行日级聚合
  - 执行数据清理
- 🏷️ 日志类型彩色标签：信息、警告、错误、数据清理、数据聚合

#### ⚙️ 系统设置优化
- 🎨 基本设置 UI 优化，采用左右布局
  - 左侧：监控配置（检测间隔、发送包数、超时时间）
  - 右侧：数据维护配置（数据保留、清理时间、聚合间隔）
- 📊 充分利用屏幕空间，消除右侧空白区域
- ⚙️ 新增数据维护配置项：
  - 原始数据保留天数（7-365天）
  - 数据清理时间（每小时可选）
  - 数据聚合间隔（1-24小时）
- 🔄 定时任务从数据库动态读取配置，支持实时更新

#### 🔐 认证系统优化
- ✅ 登录页面增加自动跳转检查
- 🔀 无管理员时自动跳转到初始化页面
- 🔒 优化初始化流程，提升用户体验

#### 🛠️ 后端 API 增强
- 🔌 `/api/databoard/stats/{timeRange}` - 获取数据看板统计
- 🔌 `/api/databoard/host/{hostId}/{timeRange}` - 获取单个主机详细统计
- 🔌 `/api/system-logs` - 获取系统日志（支持分页和筛选）
- 🔌 `/api/system-logs/cleanup` - 清理旧系统日志
- 🔌 `/api/data-maintenance/aggregate-hourly` - 手动触发小时级聚合
- 🔌 `/api/data-maintenance/aggregate-daily` - 手动触发日级聚合
- 🔌 `/api/data-maintenance/cleanup` - 手动触发数据清理

#### 💾 数据库更新
- 🆕 `system_config` 表新增字段：
  - `data_retention_days` - 原始数据保留天数（默认30天）
  - `cleanup_time` - 数据清理时间（默认03:00）
  - `aggregate_interval` - 数据聚合间隔（默认1小时）
- 🆕 新增 `ping_statistics` 表存储聚合统计数据
- 🆕 新增 `system_logs` 表记录系统操作日志
- ⚠️ 注意：升级时会自动重建数据库表，请备份旧数据

### v1.2.0 (2025-11-26)
#### 🆕 通知系统优化
- 🎨 重构通知模板系统，独立 `notification_template.py` 模块
- 📝 钉钉通知支持 Markdown 格式，提升可读性
- 🎨 服务器地址显示为蓝色可点击链接
- 🔴 “无响应”改为红色加粗显示“主机不可达”
- 🎨 延迟显示增加颜色分级（<50ms绿色、50-150ms黄色、>150ms红色）
- 🕒 钉钉通知添加通知时间字段（精确到秒）
- 🔔 支持通知模式配置：状态转换通知 / 每次异常通知
- ✅ 状态转换模式支持首次异常必须通知，恢复正常发送恢复通知

#### 📊 页面功能增强
- 📄 告警记录页面增加分页查询（中文显示）
- 🎨 告警信息自动清理 Markdown 标记，只保留emoji圆点和关键信息
- 🔍 Ping日志增加状态筛选功能（正常/异常）
- 💾 主机管理增加导出功能，Excel文件自动列宽
- 📅 导出文件名时间格式优化（例：20251126_100401）
- 🔧 监控配置UI优化，避免提示和参数调节部分重叠

#### 👤 用户管理
- 🔐 新增修改密码功能，支持修改用户名和密码
- ✅ 修改需验证原密码，修改成功后自动跳转登录页
- 🎨 表单验证优化，支持实时密码一致性检查

#### 🛠️ 技术改进
- 🗄️ 数据库添加 `last_status` 字段用于状态转换检测
- 🗄️ 数据库添加 `notification_mode` 字段用于通知模式配置
- 📦 提供 Docker 环境数据库迁移工具（`migrate_db_docker.py` 和 `migrate_db_docker.sh`）
- 🔧 后端 API 新增用户密码修改接口
- 🎨 前端代码优化，提升用户体验

### v1.1.0 (2025-11-26)
- 🔐 新增完整的登录认证系统（JWT + bcrypt）
- 👤 支持管理员账户管理，首次访问需初始化
- 🔍 仪表盘和主机管理添加搜索功能（支持主机名/地址模糊搜索）
- 🎯 仪表盘和主机管理添加状态筛选（正常/异常）
- 📄 仪表盘和主机管理添加分页功能
- 📊 优化后端日志格式，添加统一时间戳
- 🚨 优化告警日志输出，任务结束时统一汇总展示
- ⚡ 调度器配置从数据库动态读取，支持实时更新
- 🎨 登录和初始化页面UI优化，使用图标提升美观度
- 🔒 所有业务API添加认证保护
- 🐛 修复bcrypt密码长度限制问题（添加SHA256预处理）
- 🐛 修复bcrypt与passlib库兼容性问题（锁定bcrypt 4.0.1版本）
- 🐛 修复管理员初始化后页面跳转失败的问题
- 🐛 修复退出登录后的遗留请求问题
- 🐛 修复路由守卫逻辑，避免不必要的API调用

### v1.0.0 (2025-11-26)
- ✨ 初始版本发布
- 🎯 支持主机监控和自动Ping检测
- 📊 数据可视化图表展示
- 🔔 告警通知（Server酱/钉钉）
- 🐳 Docker部署支持（AMD64/ARM64多架构）
- 📥 主机批量导入/导出功能
- ⚡ 立即Ping全部主机功能
- 🕐 容器时区配置支持
- 🌐 支持局域网IP访问

## 12. 许可证

MIT License

## 13. 联系方式

如有问题或建议，欢迎反馈。

---

**祝使用愉快！** 🎉
