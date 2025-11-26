@echo off
chcp 65001 >nul
cls

echo ================================
echo    Ping监控系统 - 启动中...
echo ================================
echo.

:: 检查Python
echo [1/4] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [成功] Python已安装: %%i

:: 检查Node.js
echo [2/4] 检查Node.js环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Node.js，请先安装Node.js
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo [成功] Node.js已安装: %%i

:: 安装后端依赖
echo [3/4] 安装后端依赖...
cd backend

echo 安装Python依赖包...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo [成功] 后端依赖安装完成

:: 启动后端
echo [4/4] 启动后端服务...
start "Ping监控-后端" cmd /k "cd /d %cd% && echo 后端服务运行在 http://localhost:8000 && python main.py"

cd ..

:: 启动前端
echo [4/4] 启动前端服务...
cd frontend
start "Ping监控-前端" cmd /k "cd /d %cd% && echo 前端服务运行在 http://localhost:5173 && npm run dev"

cd ..

echo.
echo ================================
echo    启动完成！
echo ================================
echo.
echo 后端服务: http://localhost:8000
echo 前端服务: http://localhost:5173
echo API文档: http://localhost:8000/docs
echo.
echo 按任意键退出...
pause >nul
