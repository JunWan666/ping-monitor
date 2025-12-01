#!/bin/bash

echo "======================================================"
echo "Ping Monitor Docker镜像更新脚本"
echo "======================================================"
echo ""

# 配置
IMAGE_NAME="tannic666/ping-monitor:latest"
CONTAINER_NAME="ping-monitor"

# 1. 停止并删除容器
echo "正在停止容器..."
docker stop $CONTAINER_NAME 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ 容器已停止"
else
    echo "⚠ 容器不存在或已停止"
fi

echo ""
echo "正在删除容器..."
docker rm $CONTAINER_NAME 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ 容器已删除"
else
    echo "⚠ 容器不存在"
fi

# 2. 删除镜像
echo ""
echo "正在删除旧镜像..."
docker rmi $IMAGE_NAME 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ 旧镜像已删除"
else
    echo "⚠ 镜像不存在"
fi

# 3. 拉取最新镜像
echo ""
echo "正在拉取最新镜像..."
docker pull $IMAGE_NAME
if [ $? -ne 0 ]; then
    echo "✗ 拉取镜像失败"
    exit 1
fi
echo "✓ 最新镜像拉取成功"

# 4. 运行新容器
echo ""
echo "正在启动新容器..."
docker run -d \
    --name $CONTAINER_NAME \
    -p 8000:8000 \
    -v "$(pwd)/data:/app/data" \
    -e TZ=Asia/Shanghai \
    --restart unless-stopped \
    $IMAGE_NAME

if [ $? -eq 0 ]; then
    echo "✓ 容器启动成功"
    echo ""
    echo "======================================================"
    echo "更新完成！"
    echo "======================================================"
    echo "容器名称: $CONTAINER_NAME"
    echo "访问地址: http://localhost:8000"
    echo ""
    echo "查看日志: docker logs -f $CONTAINER_NAME"
    echo "======================================================"
else
    echo "✗ 容器启动失败"
    exit 1
fi
