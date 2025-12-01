#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os

def run_command(cmd, check=True):
    """执行shell命令"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        if check and result.returncode != 0:
            return False
        return True
    except Exception as e:
        print(f"命令执行失败: {e}")
        return False

def main():
    print("=" * 60)
    print("Ping Monitor Docker镜像更新脚本")
    print("=" * 60)
    print()
    
    # 配置
    IMAGE_NAME = "tannic666/ping-monitor:latest"
    CONTAINER_NAME = "ping-monitor"
    
    # 1. 停止容器
    print("正在停止容器...")
    if run_command(f"docker stop {CONTAINER_NAME}", check=False):
        print("✓ 容器已停止")
    else:
        print("⚠ 容器不存在或已停止")
    
    # 2. 删除容器
    print()
    print("正在删除容器...")
    if run_command(f"docker rm {CONTAINER_NAME}", check=False):
        print("✓ 容器已删除")
    else:
        print("⚠ 容器不存在")
    
    # 3. 删除旧镜像
    print()
    print("正在删除旧镜像...")
    if run_command(f"docker rmi {IMAGE_NAME}", check=False):
        print("✓ 旧镜像已删除")
    else:
        print("⚠ 镜像不存在")
    
    # 4. 拉取最新镜像
    print()
    print("正在拉取最新镜像...")
    if not run_command(f"docker pull {IMAGE_NAME}"):
        print("✗ 拉取镜像失败")
        input("按回车键退出...")
        return 1
    print("✓ 最新镜像拉取成功")
    
    # 5. 运行新容器
    print()
    print("正在启动新容器...")
    
    # 获取项目根目录的绝对路径（脚本在docker文件夹下，需要向上一级）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # 向上一级到项目根目录
    data_dir = os.path.join(project_root, "data")
    
    docker_run_cmd = f"""docker run -d \
        --name {CONTAINER_NAME} \
        -p 8000:8000 \
        -v "{data_dir}:/app/data" \
        -e TZ=Asia/Shanghai \
        --restart unless-stopped \
        {IMAGE_NAME}"""
    
    if not run_command(docker_run_cmd):
        print("✗ 容器启动失败")
        input("按回车键退出...")
        return 1
    
    print("✓ 容器启动成功")
    print()
    print("=" * 60)
    print("更新完成!")
    print("=" * 60)
    print(f"容器名称: {CONTAINER_NAME}")
    print(f"访问地址: http://localhost:8000")
    print()
    print(f"查看日志: docker logs -f {CONTAINER_NAME}")
    print("=" * 60)
    print()
    
    input("按回车键退出...")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"程序执行出错: {e}")
        input("按回车键退出...")
        sys.exit(1)
