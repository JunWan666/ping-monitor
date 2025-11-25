@echo off
chcp 65001 >nul
cls

echo ================================
echo    Docker启动脚本
echo ================================
echo.

:: 检查Docker
echo [1/3] 检查Docker环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Docker，请先安装Docker Desktop
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('docker --version') do echo [成功] Docker已安装: %%i

:: 构建镜像
echo [2/3] 构建Docker镜像...
docker build -t ping-monitor .
if %errorlevel% neq 0 (
    echo [错误] 镜像构建失败
    pause
    exit /b 1
)
echo [成功] 镜像构建完成

:: 启动容器
echo [3/3] 启动容器...
docker run -d --name ping-monitor -p 8000:8000 -v "%cd%\data:/app/data" --restart unless-stopped ping-monitor
if %errorlevel% neq 0 (
    echo [错误] 容器启动失败
    echo 提示: 如果容器已存在，请先运行: docker rm -f ping-monitor
    pause
    exit /b 1
)

echo.
echo ================================
echo    启动完成！
echo ================================
echo.
echo 访问地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 常用命令:
echo   查看日志: docker logs -f ping-monitor
echo   停止服务: docker stop ping-monitor
echo   启动服务: docker start ping-monitor
echo   删除容器: docker rm -f ping-monitor
echo.
pause
