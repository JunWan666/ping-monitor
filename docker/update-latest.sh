#!/bin/bash

echo "======================================================"
echo "Ping Monitor Docker镜像更新脚本"
echo "======================================================"
echo ""

# 配置
IMAGE_NAME="tannic666/ping-monitor:latest"
CONTAINER_NAME="ping-monitor"

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# 如果脚本在docker子目录，则向上一级；否则就是当前目录
if [[ "$SCRIPT_DIR" == */docker ]]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
fi
DATA_DIR="$PROJECT_ROOT/data"
BACKUP_DIR="$DATA_DIR/backups"

# 0. 备份数据库
echo "正在备份数据库..."
if [ -f "$DATA_DIR/ping_monitor.db" ]; then
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    
    # 生成备份文件名（带时间戳）
    BACKUP_FILE="$BACKUP_DIR/ping_monitor_$(date +%Y%m%d_%H%M%S).db"
    
    # 复制数据库文件
    cp "$DATA_DIR/ping_monitor.db" "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✓ 数据库已备份到: $BACKUP_FILE"
        
        # 只保留最近5个备份
        BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/ping_monitor_*.db 2>/dev/null | wc -l)
        if [ $BACKUP_COUNT -gt 5 ]; then
            echo "正在清理旧备份（保留最近5个）..."
            ls -1t "$BACKUP_DIR"/ping_monitor_*.db | tail -n +6 | xargs rm -f
            echo "✓ 旧备份已清理"
        fi
    else
        echo "✗ 数据库备份失败"
        read -p "是否继续更新？(y/N): " CONTINUE
        if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
            echo "更新已取消"
            exit 1
        fi
    fi
else
    echo "⚠ 数据库文件不存在: $DATA_DIR/ping_monitor.db"
    echo "跳过备份"
fi

echo ""

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
    -v "$DATA_DIR:/app/data" \
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
    if [ -f "$BACKUP_FILE" ]; then
        echo "数据库备份: $BACKUP_FILE"
    fi
    echo "查看日志: docker logs -f $CONTAINER_NAME"
    echo "======================================================"
else
    echo "✗ 容器启动失败"
    exit 1
fi
