# Ping Monitor 前端 UI 重构验收记录

验收日期：2026-11-20 至 2026-11-21（Asia/Shanghai）。从原工作区终端用 Playwright 1.65.1 启动 Chromium 159.0.8154.6，访问实际 FastAPI 提供的 `frontend/dist`，未使用 Vite 替代部署入口。测试主机、配置写入、初始化和 SQL 恢复均使用隔离 SQLite，通知只发到本机模拟服务器；未修改原有 `8765` 服务或生产数据。保留 `http://127.0.0.1:8767` 供本地预览。

## 页面覆盖与结果

表中 Vue 文件均位于 `frontend/src/components/`。桌面逐项点击全部 12 个菜单，核对地址栏、内容区、面包屑及高亮。移动端点过首页、主机、域名、告警、我的 5 个底栏入口，高亮和标题均跟随路由。

| 路径 | 对应文件 | 页面主体改动 | 浏览器验收 |
| --- | --- | --- | --- |
| `/admin` | `Main.vue`、`router.js`、`App.vue`、`style.css` | 浅灰工作区与白色导航；桌面分组侧栏与面包屑、移动端底栏；用 `RouterView` 渲染页面 | 默认进入仪表盘；前进、后退与菜单高亮同步 |
| `/admin/dashboard` | `Dashboard.vue`、`DashboardHostActions.vue`、`MonitorTrend.vue` | 六个旧指标归并为连通、异常、域名、近期告警四组；异常摘要显示受影响对象和可查到的最近告警时间，随后是趋势和列表；保留 Ping 全部 | 正常、离线、待检查和停用状态；1440、1280、390 px；Ping 全部命中 3 台启用主机 |
| `/admin/datascreen` | `DataScreen.vue`、`frontend/public/bigscreen/index.html` | 默认嵌在后台内容区，地图占主区；图例和工具整合，手机拆成概览、地图、排行、告警 | 中国与全球切换、拖拽、缩放复位、主题切换、悬停、固定详情和沉浸全屏 |
| `/admin/databoard` | `DataBoard.vue`、`MonitorTrend.vue`、`HostHistoryDialog.vue` | 走势与按主机对比分页签，缩小摘要区；统一百分比和毫秒双轴；单台历史只显示有数据的指标 | 6 个时间范围、真实悬停、无样本与全部超时、历史弹窗；三个主视口 |
| `/admin/hosts` | `HostManage.vue` | 搜索筛选集中，勾选后出现批量工具；状态、延迟、丢包和检测时间靠前；Ping、编辑保留行内，删除移到更多；桌面详情与移动抽屉 | 直达、刷新、搜索、编辑、启停、SSE Ping、批量 Ping、导入、导出和更多菜单删除 |
| `/admin/domains` | `DomainMonitor.vue`、`lib/domainPresentation.js` | 列表集中展示域名、监控状态、到期日、最近检查，配置与检查明细分区 | 桌面主体和移动入口、没有配置时的空态 |
| `/admin/alerts` | `AlertList.vue` | 来源、类型、时间和发送状态集中筛选；列表突出对象、消息、发生时间和通知结果 | 空态与有记录；按主机来源、不可达事件、未发送组合筛选 |
| `/admin/settings` | `Settings.vue`、`App.vue` | 探测、通知、保留和报表六组独立表单；每栏分开保存，移动端用分类选择器 | 六栏内容渲染；主机通知保存测试，模拟 Webhook 收到 1 次请求后恢复配置 |
| `/admin/settings/datascreen` | `DataScreenSettings.vue` | 基础、底图、3D、动画、预览分组，公开开关与访问说明同组 | 公开访问开、关均实际保存，预览仍需登录 |
| `/admin/logs/ping` | `Settings.vue` | 探测列表重排为目标、结果、收发包、丢包、延迟和时间；紧凑筛选和分页 | 实际 Ping 记录正常呈现 |
| `/admin/logs/system` | `SystemLogs.vue` | 按时间、类型、模块检索；列表显示消息摘要并保留详情入口 | 实际日志、直达、刷新、前进及后退 |
| `/admin/backups` | `DatabaseBackup.vue` | 导出与覆盖恢复拆成两个操作区，任务进度、阶段、日志与下载集中呈现 | 隔离库 SQL 导出、下载、导入，成功提示已执行 19 条 SQL 语句 |
| `/admin/change-password` | `UserProfile.vue` | 账号信息和密码验证分组，操作及反馈归到表单末端 | 主体和输入控件显示；未修改真实用户密码 |
| `/admin/me` | `AdminMobileMe.vue` | 移动端账户区收纳系统设置、日志和备份入口 | 390 px 底栏实际点击，标题与高亮正确 |
| `/admin/login`、`/login`、`/init` | `AdminLogin.vue`、`Login.vue`、`InitAdmin.vue` | 统一认证卡片、表单间距、主要操作和错误反馈 | 未登录深链接、通用登录入口、新库首次创建管理员 |
| `/`、`/datascreen-preview` | `DataScreen.vue`、`router.js`、`frontend/public/bigscreen/index.html` | 公开与预览共用地图界面，按入口走游客或鉴权数据 | 公开开关、游客地图、预览登录后回跳均通过 |

## 代表页截图与旧版对照

旧图为仓库中原有的真实界面基线；新图由 Chromium 连接本地隔离 FastAPI 拍摄。数据集、拍摄时点及大屏底图源不同，图中数值不能作前后对比。

| 页面 | 旧版 | 1440×900 | 1280×800 | 390×844 |
| --- | --- | --- | --- | --- |
| 仪表盘 | [旧图](images/dashboard.png) | [桌面](screenshots/ui-acceptance-2026-11-20/1440-dashboard-final.png) | [桌面](screenshots/ui-acceptance-2026-11-20/1280-dashboard-final.png) | [手机](screenshots/ui-acceptance-2026-11-20/mobile-390-dashboard-final.png) |
| 主机管理 | [旧图](images/hosts.png) | [桌面](screenshots/ui-acceptance-2026-11-20/1440-hosts-final.png) | [桌面](screenshots/ui-acceptance-2026-11-20/1280-hosts-final.png) | [手机](screenshots/ui-acceptance-2026-11-20/mobile-390-hosts-final.png) |
| 数据看板 | [旧图](images/databoard.png) | [桌面](screenshots/ui-acceptance-2026-11-20/1440-databoard-final.png) | [桌面](screenshots/ui-acceptance-2026-11-20/1280-databoard-final.png) | [手机](screenshots/ui-acceptance-2026-11-20/mobile-390-databoard-final.png) |
| 地图大屏 | [旧图](images/datascreen.png) | [桌面预览](screenshots/ui-acceptance-2026-11-20/1440-datascreen-final.png) | [桌面预览](screenshots/ui-acceptance-2026-11-20/1280-datascreen-final.png) | [概览](screenshots/ui-acceptance-2026-11-20/mobile-390-datascreen-overview-final.png)、[地图](screenshots/ui-acceptance-2026-11-20/mobile-390-datascreen-map-final.png) |

- 仪表盘：旧趋势图占去大部分首屏，新版压缩趋势，异常摘要、趋势和目标列表同屏。摘要只显示最近可查到的告警时间，不把它或最近检查时间当作异常的确切起点。参见[异常数据截图](screenshots/ui-acceptance-2026-11-20/1440-dashboard-alert-fixture-final.png)。
- 主机管理：旧版粗重的三色行内按钮改为常用操作加更多菜单；监控地址和关键读数在解析 IP、地理位置之前，附加列按宽度收起。
- 数据看板：旧版趋势和统计列表纵向堆叠，新版用页签分开纵向走势与横向对比；六个时间范围仍在工具栏，单位与悬停读数一致。
- 大屏：保持原先深色地图和两侧监控信息，整理地图工具、状态图例与区域分布；较小视口不再硬塞全部面板。常态预览不覆盖后台外壳，沉浸全屏占满视口，退出恢复导航。

补充截图：[离线与待检查](screenshots/ui-acceptance-2026-11-20/1440-host-states-fixture-final.png)、[手机详情抽屉](screenshots/ui-acceptance-2026-11-20/mobile-390-host-timeout-drawer-final.png)、[悬停](screenshots/ui-acceptance-2026-11-20/1280-databoard-hover-final.png)、[空看板](screenshots/ui-acceptance-2026-11-20/1280-databoard-no-samples-final.png)、[主机历史](screenshots/ui-acceptance-2026-11-20/1280-host-history-dialog-final.png)、[全球地图](screenshots/ui-acceptance-2026-11-20/1440-datascreen-world.png)、[全屏](screenshots/ui-acceptance-2026-11-20/1440-fullscreen-immersive-final.png)、[手机固定节点](screenshots/ui-acceptance-2026-11-20/mobile-390-datascreen-map-pinned-final.png)、[首次初始化](screenshots/ui-acceptance-2026-11-20/docker-init-deeplink-final.png)。目录内早期诊断图不作为最终验收截图。

## 回归证据

- 路由：`/admin/hosts` 未登录转到 `/admin/login?redirect=/admin/hosts`，提交后回原页；空库转到 `/init?redirect=/admin/hosts`，创建管理员后也回原页。生产静态入口直达、刷新 `/admin/hosts` 和 `/admin/logs/system`，并验证浏览器前进、后退。Docker 临时容器内再次验证深链接、初始化回跳、刷新、API 和静态资源。
- 主机操作：在 `127.0.0.1` 新建、改名、启用、停用及清理测试主机。单台 Ping 收到 10/10 包、丢包 0%；批量确认 4 个启用对象启动，跳过 1 个停用对象；导出取得 18,662 字节 XLSX，文本导入后在列表查到主机。更多菜单删除有确认，删除后记录消失。
- 数据语义：有样本的 0% 保留；无样本显示空态和占位；离线主机延迟为“超时”，丢包仍为 100%，停用与待检分开；全部丢包时不把延迟画成 `0 ms`。模拟看板请求失败时显示“数据加载失败，请刷新重试”，不同于空样本。已抽查悬停在线率 100%、丢包率 0%、平均延迟 0.35 ms。统计接口口径未更改。
- 地图：在 1440/1280 宽度验证切换主题；切全球后 ECharts 矢量底图完成渲染；拖动检查底图位移，放大、复位检查画布变化；竖屏检查旋转后悬停、固定、Esc 取消。使用同城节点验证飞线，连续刷新后排行保留 3 条真实亚毫秒读数。390 px 概览 8 个图例均在容器内，320–768 px 额外抽查无裁切。三个代表尺寸的外壳未出现横向溢出。
- 公开访问：通过设置页保存关闭后，独立访客访问 `/` 转到 `/login`，`/api/public/datascreen` 返回 403；恢复打开后，独立访客在 `/` 看到地图、公开数据返回 200。`/datascreen-preview` 未登录会重定向，登录后返回原链接并成功请求预览数据。
- 静态资源：曾发现大屏脚本缺失时收到 SPA HTML，触发 `Unexpected token '<'`。补入 `hosts_data.js` 空占位、注册 `/bigscreen` 静态挂载，缺失的带扩展名资源返回 404。大屏源与生产资源一致，均为 184,099 字节，SHA-256 为 `4ae1d77441e6c289e3406555b39b7147bac53f8bfd11b0c2fd0d0924aa75b9c9`；最终文件的三个内联脚本通过 Node 语法解析。本次使用此前已恢复并能够实际渲染的源码继续改造，未用当前构建产物反向覆盖源码。历史恢复节点记录为 177,812 字节，SHA-256 `3045a7cad3691a26c5ed6a54fbfbdcf804e1b47166abd5d012d37d38acc6dfb4`。

## 构建、接口与范围

| 检查 | 结果 |
| --- | --- |
| `cd frontend; npm run build` | 通过，2207 模块；Dockerfile 内也成功构建 |
| `git diff --check` | 通过；Windows Git 的 LF/CRLF 提示不属于空白错误 |
| FastAPI 接口烟测 | 17 个请求返回 200，包括认证、概览、主机、域名、告警、两种日志、配置、预览、公开状态和六个历史范围 |
| `pytest -q tests` | 17 passed，10 subtests passed，22 条现有 SQLAlchemy 弃用警告 |
| `docker build -f docker/Dockerfile -t ping-monitor:ui-acceptance .` | 通过；临时容器实际提供 SPA、API 与大屏资源 |

没有浏览器环境阻塞。临时 Playwright 目录为 `%TEMP%\ping-monitor-playwright-20261120135316`；通过 `require('playwright').chromium.launch({ headless: true })` 直接启动，项目未添加 Playwright 依赖。备份页查询 `import/latest` 和 `export/latest` 无活动任务时按既有接口返回 404，属预期。没有在物理手机／Safari、高德生产 Key 或 MySQL + Redis Compose 组合上做端到端复测；通知验收到本机模拟 Webhook，不代表外部平台已投递。域名真实 DNS、注册局探测与真实账号密码修改不在此次浏览器写操作范围内。

验收数据事故：准备最终截图时误清了三个隔离 SQLite 文件的历史行。其中主验收库 `e2e.sqlite3` 损失 16 条已有 Ping 记录和当时的系统日志，未恢复；已重新探测本地 QA 主机并恢复停用状态。异常样本在另一个临时库复测。工作区原有 `8765` 服务及其数据库未被该操作触及。

## 2026-11-21 二轮 UI 微调复验

本节覆盖上一版 UI 之后的调整。仍由原工作区终端启动 Playwright Chromium，访问 `http://127.0.0.1:8767` 的 FastAPI 生产构建。`before` 为本轮修改前，不是上文所列的整站改造前旧版。`after` 的域名及第五台停用主机为临时验收记录，测试后已单独删除；没有触碰 `8765` 服务。生产代码未新增 API、统计查询或项目依赖。

| 范围 | 改动及文件 | 本轮实际验证 |
| --- | --- | --- |
| 后台侧栏 | `Main.vue` 收紧子菜单内外缩进、行高和行距；二级文字保留轻微层级 | 1440 px 实测二级文字相对父级右移 5 px；逐项点击 12 个真实菜单，检查页面主体、URL 和高亮；未登录 `/admin/hosts` 登录回跳、主机和系统日志刷新、浏览器前进后退通过 |
| 仪表盘 | `Dashboard.vue` 改为五张白底简明卡片，加入当前在线率（可达的启用主机 ÷ 已启用主机；无启用主机显示占位），用箭头提示操作；列表按实际数据行数收紧 | 1440×900 和 1280×800 都完整显示 5 条，趋势面板分别约为 287、187 px，本轮改前为 162、144 px；筛选到 0 条时趋势进一步增高。验证卡片筛选、域名切换、告警跳转和 Ping 全部（3 台） |
| 数据看板 | `DataBoard.vue` 单独一排时间范围，按钮高 36 px，窄屏从 480 px 起排成两行；压缩趋势图区，不改图表口径 | 1440、1280、390、320 px 的六个选项可用且文字未裁切；图表在前两种桌面宽度约为 480、440 px，改前为 631、531 px。真实样本悬停显示 100% 在线、0% 丢包与毫秒延迟；模拟空接口响应正确显示无样本 |
| 表格 | `App.vue` 统一表头和单元格的内边距、行高基准和数字对齐；`Dashboard.vue`、`HostManage.vue`、`DomainMonitor.vue`、`DataBoard.vue`、`AlertList.vue`、`Settings.vue`、`SystemLogs.vue` 按列用途分配宽度 | 1440、1280 px 检查表头不截断、表身不横向溢出；数字、时间和操作列不挤占对象或消息列。主机单台 Ping、弹窗新增、编辑、勾选后批量 Ping（4 台、跳过 1 台停用）、文本导入和 XLSX 导出复测通过 |
| 监控域名 | `DomainMonitor.vue` 将详情弹窗换成桌面行内展开、移动端点整行展开；`DomainMonitorDetails.vue` 显示预期 NS、解析记录及值、通知状态和可用的检测结果 | 四种宽度均验证展开、收起、`?focus=` 直接展开以及独立编辑弹窗；桌面用 Enter 触发展开。测试域名显示测试 NS、配置的 A 记录 `192.0.2.10`、手填到期日及通知关闭；未对公共 DNS 或注册局发起真实探测 |
| 大屏 | 本轮未修改大屏源文件 | 1280 px 通过实际 iframe 验证地图渲染、全屏进出以及退出后顶栏与侧栏恢复；源文件和 `dist` 内副本的 SHA-256 仍一致，与上文记录相同 |

| 代表截图 | 1440 px | 1280 px | 390 px |
| --- | --- | --- | --- |
| 仪表盘 | [前](screenshots/ui-refinement-2026-11-21/desktop-1440-dashboard-before.png) · [后](screenshots/ui-refinement-2026-11-21/desktop-1440-dashboard-after.png) | [前](screenshots/ui-refinement-2026-11-21/desktop-1280-dashboard-before.png) · [后](screenshots/ui-refinement-2026-11-21/desktop-1280-dashboard-after.png) | [前](screenshots/ui-refinement-2026-11-21/mobile-390-dashboard-before.png) · [后](screenshots/ui-refinement-2026-11-21/mobile-390-dashboard-after.png) |
| 主机管理 | [前](screenshots/ui-refinement-2026-11-21/desktop-1440-hosts-before.png) · [后](screenshots/ui-refinement-2026-11-21/desktop-1440-hosts-after.png) | [前](screenshots/ui-refinement-2026-11-21/desktop-1280-hosts-before.png) · [后](screenshots/ui-refinement-2026-11-21/desktop-1280-hosts-after.png) | [前](screenshots/ui-refinement-2026-11-21/mobile-390-hosts-before.png) · [后](screenshots/ui-refinement-2026-11-21/mobile-390-hosts-after.png) |
| 数据看板 | [前](screenshots/ui-refinement-2026-11-21/desktop-1440-databoard-before.png) · [后](screenshots/ui-refinement-2026-11-21/desktop-1440-databoard-after.png) | [前](screenshots/ui-refinement-2026-11-21/desktop-1280-databoard-before.png) · [后](screenshots/ui-refinement-2026-11-21/desktop-1280-databoard-after.png) | [前](screenshots/ui-refinement-2026-11-21/mobile-390-databoard-before.png) · [后](screenshots/ui-refinement-2026-11-21/mobile-390-databoard-after.png) |
| 监控域名 | [原空列表](screenshots/ui-refinement-2026-11-21/desktop-1440-domains-before.png) · [展开](screenshots/ui-refinement-2026-11-21/desktop-1440-domains-after.png) | [展开](screenshots/ui-refinement-2026-11-21/desktop-1280-domains-after.png) | [展开](screenshots/ui-refinement-2026-11-21/mobile-390-domains-after.png) |

补充截图：[二级菜单](screenshots/ui-refinement-2026-11-21/desktop-1440-settings-menu-after.png)、[看板悬停](screenshots/ui-refinement-2026-11-21/desktop-1280-databoard-tooltip.png)、[看板空样本夹具](screenshots/ui-refinement-2026-11-21/desktop-1280-databoard-empty.png)、[后台大屏](screenshots/ui-refinement-2026-11-21/desktop-1280-map-after.png)。

本轮 `npm run build` 通过（2209 模块），`git diff --check` 通过；FastAPI 烟测 17 个请求均为 200。系统 Python 未安装 SQLAlchemy，改用现有隔离虚拟环境执行 `python -m pytest -q tests`，17 个测试、10 个子测试通过，保留 22 条既有弃用警告。未重新构建 Docker 镜像，也未重跑此前已通过的首次初始化、公开开关写入、SQL 恢复和模拟通知；对应结果见上文。未用 Safari 或实体手机验收，移动结果来自 Chromium 窄屏模拟。

## 2026-11-21 仪表盘列表交互补充复验

本次补充针对仪表盘列表的筛选和切换体验，修改集中在 `frontend/src/components/Dashboard.vue`。

- 状态筛选 Tab 增加数量角标：全部、异常 / 离线、正常、待检查、已停用；数量跟随当前搜索词更新。
- 主机表格的状态、平均延迟表头改为可排序列，支持升序和降序；超时、尚未检测和停用值按明确规则置于有数值结果之后。
- 主机列表和域名列表共用固定内容区高度，空域名数据也保留筛选区占位；切换 Tab 时卡片和表格区域高度不跳变。
- Playwright Chromium 实测 1440×900 和 390×844：角标数量正确，正常筛选返回 3 条；平均延迟升序为 0.1、0.15、0.2 ms，降序为 0.2、0.15、0.1 ms；状态升序为正常→已停用，降序反向；桌面列表区 238→238 px、移动列表区 248.4375→248.4375 px。无域名数据时显示“还没有配置监控域名”，且没有运行时错误。

截图：[桌面角标与排序](screenshots/ui-refinement-2026-11-21/desktop-1440-dashboard-status-count-sort.png)。

## 2026-11-21 仪表盘 Tab 内数量与丢包率排序复验

- `frontend/src/components/Dashboard.vue` 将状态数量从浮动角标改为 Tab 内部的紧凑小字，数量使用更小字号和浅色，选中 Tab 使用反差色；截图见 [桌面状态 Tab](screenshots/ui-refinement-2026-11-21/desktop-1440-dashboard-inline-tabs.png)。
- 主机表格的丢包率列增加自定义升序 / 降序排序，与状态、平均延迟使用相同表头交互。
- Chromium 1440×900 实测：Tab 文本为“全部 4”“异常 / 离线 0”“正常 3”“待检查 0”“已停用 1”，数量元素为普通行内布局；延迟升序 `0.1、0.15、0.2 ms`、降序 `0.2、0.15、0.1 ms`；丢包率升序和降序均正确执行。390×844 同样通过 Tab 显示与主机 / 域名切换高度检查。
- 本轮 `npm run build` 通过（2209 modules），`git diff --check` 通过。

## 2026-11-21 仪表盘五行分页容量修复

问题原因：仪表盘使用了具有固定高度的 Element Plus 表格。旧行数测量从整个表格区域开始，再减去一次表头高度，但该区域已经以表体可用高度为基准，导致接近五行边界时分页容量被算成 4。`frontend/src/lib/usePageRows.js` 现在优先用 `.el-table__body-wrapper.clientHeight` 计算桌面页容量；没有固定表格体时仍走原来的容器测量方式。

Playwright 在隔离 FastAPI 数据库临时添加两条停用主机，构造 6 条记录后验证：1640×820、1440×900 和 1280×800 每页显示 5 条，第二页显示剩余 1 条；390×844 移动视口显示 3 张主机卡片。主机 / 域名切换高度保持稳定，正常状态筛选与计数一致；临时主机已清理。构建 `npm run build` 通过（2209 modules），`git diff --check` 通过。

截图：[6 条记录时首屏显示 5 条](screenshots/ui-refinement-2026-11-21/dashboard-five-row-fix-1640.png)。

## 2026-11-22 独立可视化大屏重构验收

在视觉改造前先运行旧版大屏留图，逐项复核地图和入口行为。旧图使用脱敏的示例节点，新图使用隔离 SQLite 的测试节点，截图用于比较视觉和交互，不用于比较两组数据的指标变化。

本轮按 `unslop` 的审计、设计及复查流程，将大屏从发光仪表展示改为面向持续巡检的深色工作台。去掉装饰性星空和背景动画，保留有数据意义的节点、状态和飞线。延迟趋势上移到地图上方独立细条；把底图来源、点位数、飞线数和单位明确放在图例区。地图默认突出节点，普通地图放大后才显示省名。窄屏不再旋转界面，概览、地图、排行与告警按需切换。固定详情显示状态、延迟、丢包、位置及运营商，停用和待检查不绘制红色告警外环。`unslop` 由 Damir Sokolovsky（@heydamir）创作，CC BY 4.0；[项目来源](https://github.com/heydamir/unslop)。

| 文件 | 范围 |
| --- | --- |
| `frontend/public/bigscreen/index.html`、`screen.css` | 独立文档的区域结构、地图工具、图例、节点详情与响应式导航；样式不扩散至 Vue 外壳 |
| `frontend/public/bigscreen/screen.js` | 保留节点定位、范围、主题、地图手势和全屏；普通地图优先用本地 GeoJSON，高德验证实际底图内容后才替换普通地图；数据轮询串行，显示无样本、真实零值及失败状态 |
| `scripts/qa-bigscreen.cjs` | 用 Chromium 验证两种底图、回退路径、地图交互和预览入口；可选截图及真实高德用例，不把本地测试账号或高德 Key 写入仓库 |

### 本轮浏览器结果

| 范围 | 结果 |
| --- | --- |
| 普通地图：1440×900、1280×800、390×844、320×640 | 四种尺寸均通过中国／全球切换、地图画布、缩放复位、节点固定与关闭、主题和全屏；桌面另验节点悬停与拖拽，移动端另验四个分页和触屏命中 |
| 公开首页与预览 | 真实本地 FastAPI 的 `/` 可公开访问。匿名直达 `/admin/datascreen` 跳登录，使用本地测试用户登录后回到原 URL；`/datascreen-preview` 登录后正常加载。后台地图全屏使用浏览器全屏，退出后侧栏和顶栏恢复。以浏览器拦截将公开状态置为关闭，匿名访问首页转登录，已登录访问首页转仪表盘，鉴权预览仍可用；未为此改写设置 |
| 空态与回退 | 无可定位节点、零主机、未配置 Key、数据 API 503；SDK 阻断和 SDK 发出 `complete` 但仅有空画布时均保留普通地图。有效地图和无效画布不是同一用例 |
| 真实高德 | 使用允许的浏览器来源，并将该来源的站点请求全部拦截到本地 FastAPI；监控数据始终来自隔离测试库。SDK 200、鉴权 `10000`、真实瓦片 HTTP 成功（该轮观察到 250 个成功响应），中国及全球视图都检查了实际画面，并通过高德／普通切换。用未授权来源另外实测鉴权 `10006`，普通地图继续显示。未改高德白名单 |

高德 Web Key 仅通过生产 MySQL 的只读事务查询该字段，结束时 `ROLLBACK`；公开接口响应未提供 Key。未导出生产节点数据，未将 Key 持久化。SSH 按文档所指主机连接，未独立核验 SSH 主机指纹。未改线上数据库或配置，未部署、提交、推送，也未改动 `8765` 服务。

### 审核截图

| 场景 | 截图 |
| --- | --- |
| 桌面中国地图 | [1440 旧版](screenshots/bigscreen-unslop/before-1440.png) · [1440 新版](screenshots/bigscreen-unslop/after-china-1440.png) · [1280 新版](screenshots/bigscreen-unslop/after-china-1280.png) · [全球](screenshots/bigscreen-unslop/after-world-1440.png) |
| 窄屏 | [390 旧版](screenshots/bigscreen-unslop/before-390.png) · [390 新版](screenshots/bigscreen-unslop/after-china-390.png) · [320 新版](screenshots/bigscreen-unslop/after-china-320.png) · [移动概览](screenshots/bigscreen-unslop/after-mobile-overview.png) |
| 节点与后台 | [桌面固定详情](screenshots/bigscreen-unslop/after-node-1440.png) · [移动固定详情](screenshots/bigscreen-unslop/after-node-390.png) · [后台 iframe](screenshots/bigscreen-unslop/after-admin-1440.png) · [无定位数据](screenshots/bigscreen-unslop/after-no-coordinates.png) |
| 高德与回退 | [真实高德：中国](screenshots/bigscreen-unslop/after-amap-1440.png) · [真实高德：全球](screenshots/bigscreen-unslop/after-amap-world-1440.png) · [SDK 阻断回退](screenshots/bigscreen-unslop/after-amap-fallback.png) |

`frontend/` 下 `npm run build`、两份 JavaScript 的 `node --check`、`git diff --check` 均通过。FastAPI 返回的 HTML、CSS、JS 和两份 GeoJSON 均为 HTTP 200，下载内容与 `frontend/dist` 字节一致；公开状态、公开数据、告警及两条 SPA 深链接均返回 200，预览鉴权在浏览器中另行验证。回归通过 `node scripts/qa-bigscreen.cjs` 执行，使用原来的临时 Playwright 及本机 Chromium；未重建 Docker 镜像，未覆盖实体手机或 Safari。预览服务继续监听 `http://127.0.0.1:8767`。


## 2026-11-22 可视化大屏自由重构（已撤回的历史稿）

收到反馈后，确认前一稿仍保留原三栏排版，未达到“重新自由设计”的要求。以下布局是本轮替代版本；上文上一稿的截图不代表当前设计。

### 新设计

- **值守总览横带**：顶部统一放置五个主指标——监控节点、在线节点、平均延迟、平均丢包和异常节点；峰值与低延迟节点作为次要信息。明确区分零丢包、有实测样本的零值和暂无样本。
- **中国地图主画面**：主区跨满宽度，常态大屏不再以窄地图夹在三栏中。地图左上角放置延迟主值和趋势，切换中国／全球、底图选择、节点点选和工具保留。区域名称缩放后再显示。在线节点比例放大以适配横向地图容器。
- **横向运行明细台**：底部改为网络健康、各区域在线节点横向比较、延迟排行和异常事件四个面板，不再使用上一稿的圆环分布卡和侧栏排行。排行与事件支持面板内滚动；无事件时显示空态。
- **面向中文值守的适配**：界面标题、字段、图例和移动导航使用中文。390px 与 320px 手机改为“总览／地图／排行／事件”分屏，不对地图作横屏旋转。总览显示 5 个指标、健康状态和区域在线数；过窄时区域列表在自身面板内浏览。
- **设计系统**：更换页面主排版和信息层级，收敛为石墨底色与低饱和蓝绿地图色；红、黄、绿只表示需要辨别的监控状态。删除旧环形图与仪表 SVG，改为健康分数、三项横向比例条和同尺度区域横条。

### 本次改动文件

| 文件 | 改动 |
| --- | --- |
| `frontend/public/bigscreen/index.html` | 新的中文值守台文档结构、五项指标横排、宽幅地图、趋势信息浮层和底部四面板；移除旧仪表和区域环形图 DOM |
| `frontend/public/bigscreen/screen.css` | 自由定义的桌面布局、独立手机四屏、低饱和中国地图工作台主题、窄屏区域列表溢出处理 |
| `frontend/public/bigscreen/screen.js` | 保留现有 API／认证、调度和地图引擎；区域展示切为同量纲在线节点横条，健康指数去除旧仪表依赖；异常和排行可滚动，不分页；异常峰值每轮替换前刷新基线 |
| `scripts/qa-bigscreen.cjs` | 原有浏览器回归继续从实际本地 FastAPI 的 `frontend/dist` 运行，覆盖桌面和手机、地图操作、预览登录／全屏与失败回退 |

### 最新浏览器回归

- Playwright 实际访问 `http://127.0.0.1:8767` 提供的生产构建：1440×900、1280×800、390×844、320×640 的中国／全球地图、节点悬停或触碰、固定详情、缩放、桌面拖拽、主题切换和全屏均通过。
- 四尺寸均无页面横向溢出；手机依次检查总览、排行、事件和地图切换。0 主机、无定位、无实测、普通地图回退、SDK 阻断、SDK 完成但空底图、API 失败状态通过。桌面注入 7 条临时告警验证事件列表滚动；注入 1 台在线（0 丢包）、1 台离线、1 台待检测，验证在线率 33.3%、零值与无样本区分，以及“离线 1 · 待检 1”摘要。全站无实测样本时，平均延迟、丢包率和健康分均显示“—”。
- 后台 iframe、匿名访问跳转、登录后回到 `/admin/datascreen`、预览权限，以及地图沉浸全屏退出后侧栏／顶栏恢复通过。
- `npm run build`、`node --check frontend/public/bigscreen/screen.js`、`node --check scripts/qa-bigscreen.cjs`、`git diff --check` 通过；未部署或提交。

### 当前版本截图

| 场景 | 截图 |
| --- | --- |
| 大屏主页面 | [改造前 1440](screenshots/bigscreen-free-design-2026-11-22/before-1440.png) · [桌面 1440](screenshots/bigscreen-free-design-2026-11-22/after-china-1440.png) · [桌面 1280](screenshots/bigscreen-free-design-2026-11-22/after-china-1280.png) · [7 条事件与滚动列表](screenshots/bigscreen-free-design-2026-11-22/after-events-1440.png) · [离线／待检测混合数据](screenshots/bigscreen-free-design-2026-11-22/after-mixed-status-1280.png) · [无延迟与丢包样本](screenshots/bigscreen-free-design-2026-11-22/after-no-samples-1280.png) |
| 窄屏地图 | [手机 390 地图](screenshots/bigscreen-free-design-2026-11-22/after-china-390.png) · [手机 320 地图](screenshots/bigscreen-free-design-2026-11-22/after-china-320.png) |
| 窄屏总览 | [手机 390](screenshots/bigscreen-free-design-2026-11-22/after-overview-390.png) · [手机 320](screenshots/bigscreen-free-design-2026-11-22/after-overview-320.png) |

本轮没有再次读取线上数据库，也没有写入线上；没有部署、提交或推送。此次实际浏览器回归使用普通矢量地图和本机 FastAPI。高德接口、获准来源和真实瓦片已在上一稿验证，本次保留相同 Provider、Key 读取与失败回退逻辑，但没有在改版后的页面上重新声明已完成真实高德瓦片终验。`http://127.0.0.1:8767/` 可用于本地审核。

## 2026-11-22 值班大屏稿（已撤回的历史稿）

本稿替代上文“自由重构”稿。对照生产公开页面的实际浏览器画面，发现前稿将地图置于较矮且过宽的容器内，降低了中国轮廓的实际显示面积；延迟数值与底部排行也更接近后台小组件的阅读尺度。对照访问为公开页面 GET，未登录、未访问生产数据库，也没有写入、部署或提交。

- `frontend/public/bigscreen/index.html`、`screen.css`：改为左侧大地图和右侧数据区；左下集中四项运行指标。右上突出全网平均延迟，右下独立切换延迟排行、异常事件及区域与健康，切换不改变地图尺寸。手机默认进入地图，补充三项摘要，地图工具移到底部，保留总览、排行和事件入口。
- `frontend/public/bigscreen/screen.js`：矢量底图按画布宽高计算绘图尺寸，窗口改尺寸后重新对齐；不改变源地理数据或坐标。延迟趋势只有一个样本时仅画点，较上轮无可比值时显示“—”。继续沿用底图供应器、鉴权和本地接口，不改监控口径。
- `scripts/qa-bigscreen.cjs`：在本地 FastAPI 托管的生产构建上，添加 150 个合成节点、9 条合成事件的对照测试。1440×900 下地图画布高约 532px，中国主图范围投影宽约 743px；检查三种数据视图及 1280×800、1920×1080 重排。截图不包含生产节点、Key 或账号。

| 快照 | 说明 |
| --- | --- |
| [前稿](screenshots/bigscreen-wall-2026-11-22/before-1440-fixture.png) · [本稿](screenshots/bigscreen-wall-2026-11-22/after-1440-fixture.png) | 同一组 150 个合成节点，同为 1440×900 |
| [1920×1080](screenshots/bigscreen-wall-2026-11-22/after-1920-fixture.png) · [1280×800](screenshots/bigscreen-wall-2026-11-22/after-1280-fixture.png) · [异常事件](screenshots/bigscreen-wall-2026-11-22/after-events-fixture.png) | 同一组测试数据 |
| [390px](screenshots/bigscreen-wall-2026-11-22/after-china-390.png) · [320px](screenshots/bigscreen-wall-2026-11-22/after-china-320.png) · [后台](screenshots/bigscreen-wall-2026-11-22/after-admin-1440.png) | 隔离本地服务的数据 |

Playwright Chromium 验证普通地图、中国／全球切换、缩放、拖拽、节点详情、配色和全屏；并验证后台预览、登录后回跳、公开关闭、空态及 SDK 拒绝或空画布后的普通地图回退。这一轮未用真实高德 Key 重新验收瓦片。`npm run build`、JavaScript 语法检查和 `git diff --check` 通过。审核入口：`http://127.0.0.1:8767/`。


## 2026-11-22 恢复上游原版大屏

按用户要求停止大屏重设计。确认 `JunWan666/ping-monitor` 的 `main` 和本地基线均为 `b9fd2e5724773e9b2d4bc690ab1aa3c2ff97717f`，从该提交恢复 `frontend/public/bigscreen/index.html`；源码、生产构建及 FastAPI 实际提供的 HTML 均匹配原 Git blob `afc7a5b8eb91c5f73f9431d008f5ed353a0018b7`。撤回分离的 `screen.css`、`screen.js`、空节点占位和仅适用于改版的回归脚本。上文设计和截图仅作历史记录，后台路由、预览容器及设置页保留。

`npm run build`、`git diff --check` 通过。Playwright 实测 1440×900、1280×800 和 390×844 的原版矢量地图；另验证 1440px 主题与全屏、窄屏地图页签、后台登录回跳、独立预览和关闭公开访问时的匿名跳转。沿用原版节点导出机制，仅在本地 `frontend/dist` 为审核临时生成四个隔离测试节点；不进源码，下次干净构建会清掉。未访问线上数据库，未改线上配置、部署、提交或推送。

[恢复后 1440px](screenshots/bigscreen-upstream-restore-2026-11-22/upstream-1440.png) · [1280px](screenshots/bigscreen-upstream-restore-2026-11-22/upstream-1280.png) · [390px](screenshots/bigscreen-upstream-restore-2026-11-22/upstream-390.png)

## 2026-11-22 原版大屏地图交互优化

保留原版大屏排版，只调整地图和对应设置。`frontend/public/bigscreen/index.html` 移除飞线渲染、飞线计数及持续绘制的节点光效；保留已有节点、悬停／触摸提示、主题和图例。后台可视化设置不再显示飞线开关，现有配置字段和存取接口仍兼容。

普通地图优先使用仓库自带的中国 GeoJSON；按所有地理要素的坐标范围等比例适配，预留 HUD 和图例空间。默认与复位均为完整地图（最小 1×），最大为 3×；仅在超过可用范围的轴上允许有限拖动，避免拖到大块空白区域。滚轮、双击、按钮和双指共用同一套相机状态。拖拽、缩放和容器变化在同一帧提交底图及节点位置，地图画布空闲时不逐帧更新。手机地图不再旋转，桌面和移动端均保留地图全屏。

`node scripts/qa-bigscreen-map.cjs` 在本地 FastAPI 的生产构建上验证 1440×900、1280×800、390×844、320×640 的完整边界、缩放极限、拖动／双指、还原与全屏；四尺寸各测 950ms 静置窗口，地图节点画布重绘次数均为 0。浏览器阻断 ECharts 后，内置地图仍可缩放、限制拖动和复位；高德使用本地模拟 SDK 回归相机适配，未验真实瓦片。生产构建、内联脚本语法检查、`git diff --check` 和本地接口烟测通过；未改线上。

[桌面完整地图](screenshots/bigscreen-map-fit-2026-11-22/fit-1440.png) · [手机完整地图](screenshots/bigscreen-map-fit-2026-11-22/fit-390.png) · [内置地图兜底](screenshots/bigscreen-map-fit-2026-11-22/fallback-fit.png)

## 2026-11-22 中国主图取景与主机热点

- 只调整原版大屏的地图区域。中国矢量地图默认以包含海南的中国主图取景，远南离岛不再撑大默认范围；仅调整渲染数据，保留仓库原始 GeoJSON。高德与内置地图也以主图为默认取景，继续沿用 1×–3× 及拖拽边界，不恢复飞线。
- 地图节点继续使用现有状态颜色，放大光点并增加同城主机数。单台主机的城市也可标注，密集处自动避让；最多 5 个桌面／3 个手机热点有轻量脉冲，低性能与减少动态效果模式只保留静态光环。桌面悬停或手机点按节点与标签可看主机详情。
- 本地 FastAPI + Playwright Chromium 通过 1440×900、1280×800、390×844、320×640：检查海南位置、远南默认不展示、城市数量、节点详情、1×/3×、拖拽／双指、复位及全屏；55 台合成节点验证密集标签不重叠及减少动态效果。950 ms 静置抽查每个尺寸的地图 Canvas 重绘不超过 2 次。真实高德瓦片未重测，仅验证模拟 SDK；未访问或修改线上服务。
- `npm run build`、内联 JS 语法检查与 `git diff --check` 通过；本地大屏 HTML、GeoJSON、公开访问状态和公开大屏数据接口均返回 HTTP 200，静态文件与生产构建一致。
- 截图由同一组本轮合成夹具生成：[1440 桌面](screenshots/bigscreen-map-focus-2026-11-22/fit-1440.png) · [1280 桌面](screenshots/bigscreen-map-focus-2026-11-22/fit-1280.png) · [390 手机](screenshots/bigscreen-map-focus-2026-11-22/fit-390.png) · [320 手机](screenshots/bigscreen-map-focus-2026-11-22/fit-320.png) · [55 台密集分布](screenshots/bigscreen-map-focus-2026-11-22/dense-1440.png)。旧取景见上节（测试数据不同）。

## 2026-11-22 固定底图首帧与省区详情

- 原版大屏保持原有排版和中国主图取景。刷新不再先画简化轮廓，也不请求外部 ECharts CDN；Vite 将现有依赖的运行时构建到大屏目录，底图从本地加载。地图资源失败时明确提示，不切换轮廓。高德仍可在已有 Key 时手动切换，未重测真实瓦片。
- 接口响应之前不展示静态节点、预设控制中心或模拟趋势。使用现有公开／预览接口的坐标和监控状态，区分停用、未检测和离线。无有效经纬度的主机仍可出现在数据列表中，不放置假节点；更新或短时断线保留地图取景，上次成功的数据有断线提示。控制中心采用同一条接口记录的经纬度和城市。
- 点击省区高亮并显示主机及在线数，可进主机详情；点击城市标签、节点或控制中心也能查看对应信息。水波纹独立于地图画布，尊重动画设置、性能降级与减少动态效果。保留限位、复位、主题、地图全屏及双指缩放；移除触屏合成双击触发的缩放。
- 本地 FastAPI 生产构建上的 Playwright 回归：1920×945、1440×900、390×844 所测首屏、慢接口、正常更新、断线和重载均保持底图尺寸、投影及缩放；确认控制中心坐标、0.2 ms 的原始数值、各主机状态、省区空态、选中态随数据更新和一次性水波纹回收；另通过 1280×800、320×640 边界与缩放、密集标签及缩减动效、缺失地图资源，以及模拟高德相机。生产构建、内联脚本解析、`git diff --check` 和公开接口烟测通过；匿名预览接口返回 403。未访问或修改线上服务。

[1920 数据到达前](screenshots/bigscreen-stable-map-2026-11-22/map-first-1920.png) · [1920 数据到达后](screenshots/bigscreen-stable-map-2026-11-22/map-with-hosts-1920.png) · [1920 省区详情](screenshots/bigscreen-stable-map-2026-11-22/province-selected-1920.png) · [手机省区详情](screenshots/bigscreen-stable-map-2026-11-22/province-selected-390.png)。对照截图使用同组 API 测试夹具。

## 2026-11-23 小区域标记与地图悬停

- 中国矢量地图的省区悬停使用独立 SVG 高亮图层，沿真实省界绘制；离开后淡出，和点击锁定的省区互不干扰。仍使用同一底图、取景和相机，不恢复飞线。高德适配继续用模拟 SDK 验证，省界悬停仅用于中国矢量地图。
- 北京、天津、上海、香港、澳门优先使用带短引线的聚合标签。只避让标签，不移动主机坐标；港澳可按区域聚合不同城市字段，同城多主机点击后打开完整列表。标签可键盘操作或触摸，双指从标签上开始仍能缩放。
- 控制中心使用错峰的双圈短波，在原坐标向外扩散后淡出。兼容关闭动画、减少动态效果和现有低帧率降级；截图定格了实际 CSS 动画的一帧。点击反馈与中心水波纹分层，连续点击只保留最近一次反馈。
- 本地生产构建 Playwright 覆盖 1920×945、1440×900、1280×800、390×844、320×640。27 台合成主机在 1920 和 390 宽度均显示五个不相互重叠的小区域标签；验证香港 5 台列表、桌面键盘打开、手机轻点、悬停离开后仍保持选中、中心波纹与减少动态效果。地图首屏与刷新、拖动、双指、缩放上下限和全屏回归，前端构建、公开接口烟测及 git diff --check 均通过。未访问或修改线上服务。

[桌面省区悬停](screenshots/bigscreen-region-focus-2026-11-23/province-hover-1920.png) · [控制中心波纹定格](screenshots/bigscreen-region-focus-2026-11-23/center-ripple-1920.png) · [手机小区域标签](screenshots/bigscreen-region-focus-2026-11-23/compact-390.png) · [手机聚合详情](screenshots/bigscreen-region-focus-2026-11-23/compact-selected-390.png)

## 2026-11-23 呼吸灯、中心波纹与扫描

- 对照原版横向扫描和中心声呐效果，保持原底图、节点坐标和交互。控制中心的亮点及少量城市光点缓慢呼吸，两道错开的波纹从实际控制中心坐标扩散；扫描亮带从上往下经过地图主图，在节点和标签下方显示。不恢复飞线。
- 轻量 CSS 动效与地图画布分层，低帧率模式仍保留扫描、呼吸和中心波纹。显式关闭动画或系统要求减少动态效果时，关闭这三种动效并保留静态标记。
- 本地 Playwright 实测 1920 和 390 宽度在低帧率状态下的呼吸明暗差、扫描位移和双圈尺寸变化，波纹中心与控制中心标记吻合。验证关闭动画、减少动态效果、固定底图首帧、缩放、拖动、全屏及省区交互。完整回归覆盖 1920、1440、1280、390、320 宽度，生产构建、内联脚本解析、公开接口烟测及 git diff --check 均通过。未访问或修改线上服务。

[桌面动效定格](screenshots/bigscreen-motion-2026-11-23/map-motion-1920.png) · [手机动效定格](screenshots/bigscreen-motion-2026-11-23/map-motion-390.png)
