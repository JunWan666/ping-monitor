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

    # 获取版本号
    version_tag = input("请输入要构建的版本号 (例如: 1.3.0): ").strip()
    if not version_tag:
        print("错误：必须提供版本号")
        input("按回车键退出...")
        return 1

    # 自动添加'v'前缀如果不存在
    if not version_tag.startswith('v'):
        display_version = 'v' + version_tag
    else:
        display_version = version_tag
        
    # 移除开头的'v'字符用于标签命名
    clean_version = display_version[1:] if display_version.startswith('v') else display_version

    print()
    print("准备构建以下镜像标签：")
    print(f"1. {docker_username}/{docker_repository}:{clean_version}-amd64")
    print(f"2. {docker_username}/{docker_repository}:{clean_version}-arm64")
    print(f"3. {docker_username}/{docker_repository}:latest-amd64")
    print(f"4. {docker_username}/{docker_repository}:latest-arm64")
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

    # 构建并推送AMD64架构镜像
    print()
    print("开始构建AMD64架构镜像...")
    print()

    print(f"构建并推送 {docker_username}/{docker_repository}:{clean_version}-amd64")
    result = subprocess.run([
        "docker", "buildx", "build", "--platform", "linux/amd64",
        "-t", f"{docker_username}/{docker_repository}:{clean_version}-amd64",
        "--push",
        "-f", "docker/Dockerfile",
        "."
    ], cwd="..")
    
    if result.returncode != 0:
        print("错误：AMD64架构镜像构建失败")
        input("按回车键退出...")
        return 1

    print(f"构建并推送 {docker_username}/{docker_repository}:latest-amd64")
    result = subprocess.run([
        "docker", "buildx", "build", "--platform", "linux/amd64",
        "-t", f"{docker_username}/{docker_repository}:latest-amd64",
        "--push",
        "-f", "docker/Dockerfile",
        "."
    ], cwd="..")
    
    if result.returncode != 0:
        print("错误：AMD64架构latest镜像构建失败")
        input("按回车键退出...")
        return 1

    # 构建并推送ARM64架构镜像
    print()
    print("开始构建ARM64架构镜像...")
    print()

    print(f"构建并推送 {docker_username}/{docker_repository}:{clean_version}-arm64")
    result = subprocess.run([
        "docker", "buildx", "build", "--platform", "linux/arm64",
        "-t", f"{docker_username}/{docker_repository}:{clean_version}-arm64",
        "--push",
        "-f", "docker/Dockerfile",
        "."
    ], cwd="..")
    
    if result.returncode != 0:
        print("错误：ARM64架构镜像构建失败")
        input("按回车键退出...")
        return 1

    print(f"构建并推送 {docker_username}/{docker_repository}:latest-arm64")
    result = subprocess.run([
        "docker", "buildx", "build", "--platform", "linux/arm64",
        "-t", f"{docker_username}/{docker_repository}:latest-arm64",
        "--push",
        "-f", "docker/Dockerfile",
        "."
    ], cwd="..")
    
    if result.returncode != 0:
        print("错误：ARM64架构latest镜像构建失败")
        input("按回车键退出...")
        return 1

    # 创建并推送Manifest清单以支持多架构
    print()
    print("创建多架构Manifest清单...")
    print()

    print(f"创建 {clean_version} 版本的多架构清单")
    subprocess.run([
        "docker", "manifest", "create", 
        f"{docker_username}/{docker_repository}:{clean_version}",
        f"{docker_username}/{docker_repository}:{clean_version}-amd64",
        f"{docker_username}/{docker_repository}:{clean_version}-arm64"
    ])
    
    subprocess.run([
        "docker", "manifest", "annotate",
        f"{docker_username}/{docker_repository}:{clean_version}",
        f"{docker_username}/{docker_repository}:{clean_version}-amd64",
        "--arch", "amd64", "--os", "linux"
    ])
    
    subprocess.run([
        "docker", "manifest", "annotate",
        f"{docker_username}/{docker_repository}:{clean_version}",
        f"{docker_username}/{docker_repository}:{clean_version}-arm64",
        "--arch", "arm64", "--os", "linux"
    ])
    
    subprocess.run([
        "docker", "manifest", "push",
        f"{docker_username}/{docker_repository}:{clean_version}"
    ])

    print("创建 latest 版本的多架构清单")
    subprocess.run([
        "docker", "manifest", "create", 
        f"{docker_username}/{docker_repository}:latest",
        f"{docker_username}/{docker_repository}:latest-amd64",
        f"{docker_username}/{docker_repository}:latest-arm64"
    ])
    
    subprocess.run([
        "docker", "manifest", "annotate",
        f"{docker_username}/{docker_repository}:latest",
        f"{docker_username}/{docker_repository}:latest-amd64",
        "--arch", "amd64", "--os", "linux"
    ])
    
    subprocess.run([
        "docker", "manifest", "annotate",
        f"{docker_username}/{docker_repository}:latest",
        f"{docker_username}/{docker_repository}:latest-arm64",
        "--arch", "arm64", "--os", "linux"
    ])
    
    subprocess.run([
        "docker", "manifest", "push",
        f"{docker_username}/{docker_repository}:latest"
    ])

    print()
    print("=" * 50)
    print("构建和推送完成！")
    print("=" * 50)
    print("镜像信息：")
    print(f"  版本：{docker_username}/{docker_repository}:{clean_version}")
    print(f"  最新：{docker_username}/{docker_repository}:latest")
    print()
    print("这些镜像支持以下架构：")
    print("  - AMD64 (x86_64)")
    print("  - ARM64 (aarch64)")
    print()
    print("使用方法：")
    print(f"  docker pull {docker_username}/{docker_repository}:{clean_version}")
    print(f"  docker run -d -p 8000:8000 {docker_username}/{docker_repository}:{display_version}")
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