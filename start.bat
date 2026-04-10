@echo off
chcp 65001 >nul
cls

echo ================================
echo    Ping监控系统 - 启动中...
echo ================================
echo.

echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [成功] %%i

echo [2/5] 检查 Node.js 环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo [成功] Node.js %%i

echo [3/5] 安装后端依赖...
cd backend
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo [成功] 后端依赖安装完成
cd ..

echo [4/5] 检查前端依赖...
if not exist frontend\node_modules (
    echo 未检测到 frontend\node_modules，开始执行 npm install ...
    cd frontend
    npm install
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
    cd ..
) else (
    echo [成功] 前端依赖已存在
)

echo [5/5] 启动服务...
cd backend
start "Ping监控-后端" cmd /k "cd /d %cd% && set UVICORN_RELOAD=true && echo 后端服务运行于 http://localhost:8000 && python main.py"
cd ..

cd frontend
start "Ping监控-前端" cmd /k "cd /d %cd% && echo 前端服务运行于 http://localhost:5173 && npm run dev"
cd ..

echo.
echo ================================
echo    启动完成
echo ================================
echo.
echo 后端服务: http://localhost:8000
echo 前端服务: http://localhost:5173
echo API 文档: http://localhost:8000/docs
echo.
echo 按任意键退出...
pause >nul
