#!/bin/bash
# Docker环境数据库迁移脚本

echo "========================================="
echo "  Ping监控系统 - 数据库迁移工具"
echo "========================================="
echo ""

# 检查是否提供了容器名称
if [ -z "$1" ]; then
    echo "用法: ./migrate_db_docker.sh <容器名称或ID>"
    echo ""
    echo "示例: ./migrate_db_docker.sh ping-monitor"
    echo ""
    exit 1
fi

CONTAINER_NAME=$1

# 检查容器是否运行
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ 容器 '${CONTAINER_NAME}' 未运行或不存在"
    echo ""
    echo "运行中的容器列表："
    docker ps --format "table {{.Names}}\t{{.Status}}"
    exit 1
fi

echo "容器名称: ${CONTAINER_NAME}"
echo "开始数据库迁移..."
echo ""

# 执行迁移脚本
docker exec ${CONTAINER_NAME} python /app/migrate_db_docker.py

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "  ✅ 数据库迁移成功完成！"
    echo "========================================="
    echo ""
    echo "下一步操作："
    echo "1. 重启容器使更改生效"
    echo "   docker restart ${CONTAINER_NAME}"
    echo ""
else
    echo ""
    echo "========================================="
    echo "  ❌ 数据库迁移失败"
    echo "========================================="
    echo ""
    echo "请检查："
    echo "1. 数据目录是否正确挂载"
    echo "2. 数据库文件路径是否正确"
    echo "3. 容器内是否有Python环境"
    echo ""
    exit 1
fi
