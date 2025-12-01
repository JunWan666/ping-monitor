#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import json
import urllib.request
import urllib.error

def check_docker():
    """检查Docker是否安装"""
    print("检查Docker环境...")
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Docker版本: {result.stdout.strip()}")
            return True
        else:
            print("错误：未检测到Docker，请先安装Docker Desktop")
            return False
    except FileNotFoundError:
        print("错误：未检测到Docker，请先安装Docker Desktop")
        return False

def check_buildx():
    """检查Docker Buildx是否可用"""
    print("检查Docker Buildx...")
    try:
        result = subprocess.run(["docker", "buildx", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Buildx版本: {result.stdout.strip()}")
            return True
        else:
            print("错误：Docker Buildx不可用，请确保Docker Desktop版本较新")
            return False
    except FileNotFoundError:
        print("错误：Docker Buildx不可用，请确保Docker Desktop版本较新")
        return False

def get_docker_hub_tags(username, repository):
    """查询Docker Hub上的标签"""
    print("正在查询Docker Hub上的现有版本...")
    print()
    
    try:
        url = f"https://hub.docker.com/v2/repositories/{username}/{repository}/tags/"
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        
        if 'results' in data:
            print("已发布的版本标签：")
            print("------------------")
            for tag_info in data['results']:
                tag_name = tag_info.get('name', '')
                if tag_name:
                    print(f"  {tag_name}")
            print()
            return True
        else:
            print("无法获取标签信息")
            return False
            
    except urllib.error.URLError as e:
        print(f"网络错误: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return False
    except Exception as e:
        print(f"查询标签时发生错误: {e}")
        return False

def main():
    print("=" * 50)
    print("Ping Monitor Docker镜像构建和推送工具")
    print("=" * 50)
    print()

    # 检查环境
    if not check_docker():
        input("按回车键退出...")
        return 1
    
    if not check_buildx():
        input("按回车键退出...")
        return 1

    # 登录Docker Hub
    print()
    print("登录Docker Hub以查询现有版本和推送镜像")
    print("请确保您已拥有Docker Hub账户并具有相应仓库的推送权限")
    print()

    # 获取用户输入
    docker_username = input("请输入Docker Hub用户名 (默认: tannic666): ").strip()
    if not docker_username:
        docker_username = "tannic666"

    docker_repository = input("请输入Docker Hub仓库名 (默认: ping-monitor): ").strip()
    if not docker_repository:
        docker_repository = "ping-monitor"

    # 查询现有版本
    print()
    get_docker_hub_tags(docker_username, docker_repository)

    print("注意：如果上面没有显示任何版本，可能是因为：")
    print("1. 仓库不存在")
    print("2. 仓库是私有的且您尚未登录")
    print("3. 网络连接问题")
    print()

    # 选择推送模式
    print("请选择推送模式:")
    print("1. 只推送版本标签 (需要输入版本号)")
    print("2. 只推送latest标签")
    print("3. 同时推送版本和latest标签 (推荐)")
    print()
    push_mode = input("请输入选项 (1/2/3，默认3): ").strip()
    if not push_mode:
        push_mode = '3'
    
    if push_mode not in ['1', '2', '3']:
        print("错误：无效的选项,请输入1、2或3")
        input("按回车键退出...")
        return 1

    # 根据推送模式决定是否需要版本号
    clean_version = None
    display_version = None
    
    if push_mode in ['1', '3']:
        # 获取版本号
        print()
        version_tag = input("请输入要构建的版本号 (例如: 1.3.0): ").strip()
        if not version_tag:
            print("错误：必须提供版本号")
            input("按回车键退出...")
            return 1

        # 自动添加'v'前缀如果不存在
        if not version_tag.startswith('v'):
            clean_version = 'v' + version_tag
        else:
            clean_version = version_tag

    print()
    print("准备构建以下镜像标签：")
    
    if push_mode in ['1', '3']:
        print(f"- {docker_username}/{docker_repository}:{clean_version} (支持amd64/arm64)")
    
    if push_mode in ['2', '3']:
        print(f"- {docker_username}/{docker_repository}:latest (支持amd64/arm64)")
    
    print()

    # 确认构建
    confirm = input("确认开始构建？(y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("取消构建")
        input("按回车键退出...")
        return 0

    # 创建Buildx构建器实例
    print()
    print("创建Docker Buildx构建器实例...")
    subprocess.run(["docker", "buildx", "create", "--name", "mybuilder", "--use"], 
                  capture_output=True, text=True)
    subprocess.run(["docker", "buildx", "inspect", "--bootstrap", "mybuilder"], 
                  capture_output=True, text=True)

    # 构建多架构镜像（直接推送Manifest，不推送带后缀的单架构镜像）
    print()
    print("开始构建多架构镜像...")
    print()

    # 构建版本标签
    if push_mode in ['1', '3']:
        print(f"构建并推送多架构镜像: {docker_username}/{docker_repository}:{clean_version}")
        
        # 获取项目根目录（docker文件夹的上级目录）
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        result = subprocess.run([
            "docker", "buildx", "build",
            "--platform", "linux/amd64,linux/arm64",
            "-t", f"{docker_username}/{docker_repository}:{clean_version}",
            "--push",
            "-f", "docker/Dockerfile",
            "."
        ], cwd=project_root)
        
        if result.returncode != 0:
            print("错误：版本镜像构建失败")
            input("按回车键退出...")
            return 1

    # 构建latest标签
    if push_mode in ['2', '3']:
        print(f"构建并推送多架构镜像: {docker_username}/{docker_repository}:latest")
        
        # 获取项目根目录（docker文件夹的上级目录）
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        result = subprocess.run([
            "docker", "buildx", "build",
            "--platform", "linux/amd64,linux/arm64",
            "-t", f"{docker_username}/{docker_repository}:latest",
            "--push",
            "-f", "docker/Dockerfile",
            "."
        ], cwd=project_root)
        
        if result.returncode != 0:
            print("错误：latest镜像构建失败")
            input("按回车键退出...")
            return 1

    # Buildx会自动创建多架构Manifest，无需手动创建
    print()
    print("多架构镜像构建完成！")
    print("Buildx已自动创建Manifest清单，支持AMD64和ARM64架构")

    print()
    print("="  * 50)
    print("构建和推送完成！")
    print("=" * 50)
    print("镜像信息：")
    
    if push_mode in ['1', '3']:
        print(f"  版本：{docker_username}/{docker_repository}:{clean_version}")
    if push_mode in ['2', '3']:
        print(f"  最新：{docker_username}/{docker_repository}:latest")
    
    print()
    print("这些镜像支持以下架构：")
    print("  - AMD64 (x86_64)")
    print("  - ARM64 (aarch64)")
    print()
    print("使用方法：")
    
    if push_mode in ['1', '3']:
        print(f"  docker pull {docker_username}/{docker_repository}:{clean_version}")
        print(f"  docker run -d -p 8000:8000 {docker_username}/{docker_repository}:{clean_version}")
    if push_mode in ['2', '3']:
        print(f"  docker pull {docker_username}/{docker_repository}:latest")
        print(f"  docker run -d -p 8000:8000 {docker_username}/{docker_repository}:latest")
    
    print()
    
    input("按回车键退出...")

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