# Ping监控系统

一个基于 FastAPI + Vue3 + Element Plus 的网络主机监控系统，支持自动化 Ping 检测、告警通知和数据可视化。

## 功能特性

### 核心功能
- 🔍 **主机监控** - 支持添加多个主机，实时监控网络状态
- 📊 **数据可视化** - 使用 ECharts 展示延迟和丢包率趋势
- 🔔 **告警通知** - 支持 Server酱 和 Webhook（钉钉）通知
- ⏰ **定时检测** - 自动按设定间隔执行 Ping 检测
- 📝 **日志记录** - 完整的 Ping 日志记录和查询
- ⚙️ **灵活配置** - 可自定义检测间隔、超时时间、告警阈值等

### 界面功能
- **仪表盘** - 查看所有主机的实时状态和统计信息
- **主机管理** - 添加、编辑、删除监控主机，支持手动 Ping 和 Excel 导入/导出
- **告警记录** - 查看历史告警信息
- **系统设置** - 配置检测参数和通知方式
- **Ping日志** - 查看详细的 Ping 检测记录，支持分页和筛选

## 技术栈

### 后端
- **FastAPI** - 现代化的 Python Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **SQLite** - 轻量级数据库
- **APScheduler** - 定时任务调度
- **ping3** - Python Ping 实现

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Element Plus** - Vue 3 组件库
- **ECharts** - 数据可视化图表
- **Axios** - HTTP 客户端
- **Vite** - 现代化构建工具

## 项目结构

```
ping-monitor/
├── backend/                  # 后端目录
│   ├── main.py              # FastAPI 主程序和 API 路由
│   ├── database.py          # 数据库模型定义
│   ├── ping_service.py      # Ping 检测服务
│   ├── scheduler.py         # 定时任务调度器
│   ├── notification.py      # 通知服务（Server酱/Webhook）
│   └── requirements.txt     # Python 依赖
│
├── frontend/                # 前端目录
│   ├── src/
│   │   ├── components/      # Vue 组件
│   │   │   ├── Dashboard.vue      # 仪表盘
│   │   │   ├── HostManage.vue     # 主机管理
│   │   │   ├── AlertList.vue      # 告警记录
│   │   │   └── Settings.vue       # 系统设置
│   │   ├── App.vue          # 主应用组件
│   │   ├── api.js           # API 接口封装
│   │   └── main.js          # 入口文件
│   ├── package.json         # Node 依赖
│   └── vite.config.js       # Vite 配置
│
├── start.bat                # Windows 一键启动脚本
├── ping_monitor.db          # SQLite 数据库（运行后生成）
└── README.md                # 项目说明文档
```

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 14+
- Windows/Linux/macOS

### 安装步骤

#### 方法一：一键启动（Windows）
```bash
# 双击运行 start.bat 文件，自动安装依赖并启动服务
start.bat
```

#### 方法二：手动启动

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

### 访问系统
- **前端界面**：http://localhost:5173
- **API 文档**：http://localhost:8000/docs
- **API 接口**：http://localhost:8000/api

## 使用说明

### 1. 添加监控主机
1. 进入「主机管理」页面
2. 点击「添加主机」按钮
3. 填写主机信息：
   - **主机名称**：便于识别的名称
   - **主机地址**：IP 地址或域名
   - **描述**：可选的说明信息
   - **告警阈值**：丢包率超过此值时触发告警（默认 20%）
4. 点击「确定」保存

### 2. 配置系统参数
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

### 3. 查看监控数据
- **仪表盘**：查看所有主机的实时状态、延迟、丢包率
- **告警记录**：查看触发的告警信息
- **Ping日志**：查看详细的检测记录，支持按主机筛选和分页

### 4. 手动执行 Ping
1. 在「主机管理」页面，点击主机操作栏的「Ping」按钮
2. 系统会立即执行 Ping 检测并显示结果
3. 检测过程中可以点击「取消」按钮中断操作

### 5. 批量导入主机
1. 在「主机管理」页面，点击「导入主机」
2. 选择 Excel 文件（支持 .xlsx 格式）
3. Excel 表格需包含列：主机名称、主机地址、描述、告警阈值
4. 系统会自动导入并创建主机

### 6. 导出主机列表
1. 在「主机管理」页面，点击「导出主机」
2. 系统会生成 Excel 文件并自动下载
3. 文件包含所有主机的完整信息

## API 接口

### 主机管理
- `GET /api/hosts` - 获取所有主机
- `POST /api/hosts` - 添加主机
- `GET /api/hosts/{id}` - 获取单个主机
- `PUT /api/hosts/{id}` - 更新主机
- `DELETE /api/hosts/{id}` - 删除主机

### Ping 操作
- `POST /api/ping/{id}` - 立即执行 Ping
- `GET /api/ping/logs` - 获取 Ping 日志（支持分页和筛选）

### 监控数据
- `GET /api/dashboard` - 获取仪表盘数据
- `GET /api/records/{id}` - 获取主机监控记录
- `GET /api/alerts` - 获取告警记录

### 系统配置
- `GET /api/config` - 获取系统配置
- `PUT /api/config` - 更新系统配置
- `POST /api/test-notification/{type}` - 测试通知功能

详细的 API 文档请访问：http://localhost:8000/docs

## 数据库结构

### hosts（主机表）
- `id` - 主机 ID
- `name` - 主机名称（唯一）
- `address` - IP 地址或域名
- `description` - 描述信息
- `enabled` - 是否启用监控
- `alert_threshold` - 告警阈值（丢包率 %）
- `created_at` - 创建时间

### ping_records（Ping 记录表）
- `id` - 记录 ID
- `host_id` - 关联主机 ID
- `packet_sent` - 发送包数
- `packet_received` - 接收包数
- `packet_loss` - 丢包率（%）
- `min_rtt` - 最小延迟（ms）
- `max_rtt` - 最大延迟（ms）
- `avg_rtt` - 平均延迟（ms）
- `created_at` - 检测时间

### alerts（告警表）
- `id` - 告警 ID
- `host_id` - 关联主机 ID
- `host_name` - 主机名称
- `alert_type` - 告警类型
- `message` - 告警消息
- `is_sent` - 是否已发送通知
- `created_at` - 告警时间

### system_config（系统配置表）
- `id` - 配置 ID
- `check_interval` - 检测间隔（分钟）
- `packet_count` - 发送包数
- `packet_timeout` - 超时时间（秒）
- `serverchan_key` - Server酱密钥
- `webhook_url` - Webhook 地址
- `webhook_secret` - Webhook 加签密钥
- `updated_at` - 更新时间

## 通知配置

### Server酱
1. 访问 [Server酱官网](https://sct.ftqq.com/) 注册账号
2. 获取 SendKey
3. 在系统设置中填入 SendKey
4. 点击「测试通知」验证配置

### 钉钉机器人
1. 在钉钉群中添加自定义机器人
2. 获取 Webhook 地址和加签密钥
3. 在系统设置中填入配置
4. 点击「测试通知」验证配置

## 常见问题

### Q: 后端启动失败，提示 "需要管理员权限"
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

## 开发说明

### 后端开发
```bash
cd backend
# 开发模式运行（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发
```bash
cd frontend
# 开发模式运行（热更新）
npm run dev

# 构建生产版本
npm run build
```

### 添加新功能
1. 后端：在 `main.py` 中添加 API 路由
2. 前端：在 `components/` 中创建 Vue 组件
3. 数据库：在 `database.py` 中修改模型定义

## 更新日志

### v1.0.0 (2025-11-25)
- ✨ 初始版本发布
- 🎯 支持主机监控和 Ping 检测
- 📊 数据可视化和告警通知
- 🔧 系统配置和日志查询
- 📥 主机批量导入/导出功能

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎反馈。

---

**祝使用愉快！** 🎉
