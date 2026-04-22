#!/usr/bin/env bash

set -Eeuo pipefail
trap 'printf "[ERROR] 脚本执行失败：第 %s 行命令 %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"

DEFAULT_IMAGE="tannic666/ping-monitor:v1.5.0"
IMAGE="${PING_MONITOR_IMAGE:-$DEFAULT_IMAGE}"
INSTALL_ONLY=0
DEPLOY_ONLY=0
SKIP_DAEMON_MIRROR=0

log() {
    printf '[INFO] %s\n' "$1"
}

warn() {
    printf '[WARN] %s\n' "$1"
}

die() {
    printf '[ERROR] %s\n' "$1" >&2
    exit 1
}

build_compose_cmd() {
    local cmd=(docker compose)
    if [[ -f "$ENV_FILE" ]]; then
        cmd+=(--env-file "$ENV_FILE")
    fi
    cmd+=(-f "$COMPOSE_FILE")
    printf '%s\n' "${cmd[@]}"
}

usage() {
    cat <<'EOF'
用法：
  sudo bash scripts/deploy-docker-debian11.sh [选项]

选项：
  --image <镜像>
      指定部署镜像，默认使用 tannic666/ping-monitor:v1.5.0

  --install-only
      仅安装 Docker，不部署应用

  --deploy-only
      跳过 Docker 安装，仅部署应用

  --skip-daemon-mirror
      不修改 /etc/docker/daemon.json

  -h, --help
      显示帮助

示例：
  sudo bash scripts/deploy-docker-debian11.sh
  sudo bash scripts/deploy-docker-debian11.sh --image tannic666/ping-monitor:latest
  sudo bash scripts/deploy-docker-debian11.sh --install-only
  sudo bash scripts/deploy-docker-debian11.sh --deploy-only
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            [[ $# -ge 2 ]] || die "--image 需要参数"
            IMAGE="$2"
            shift 2
            ;;
        --install-only)
            INSTALL_ONLY=1
            shift
            ;;
        --deploy-only)
            DEPLOY_ONLY=1
            shift
            ;;
        --skip-daemon-mirror)
            SKIP_DAEMON_MIRROR=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "未知参数：$1"
            ;;
    esac
done

[[ "$INSTALL_ONLY" -eq 1 && "$DEPLOY_ONLY" -eq 1 ]] && die "--install-only 与 --deploy-only 不能同时使用"

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        die "请使用 root 或 sudo 执行本脚本"
    fi
}

install_docker_repo() {
    log "安装 Docker 依赖..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release apt-transport-https

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian $(lsb_release -cs) stable
EOF

    apt-get update
}

install_docker_packages() {
    log "安装 Docker CE / Compose 插件..."
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

configure_docker_daemon() {
    if [[ "$SKIP_DAEMON_MIRROR" -eq 1 ]]; then
        warn "已跳过 Docker daemon 镜像加速配置"
        return
    fi

    mkdir -p /etc/docker

    if [[ -f /etc/docker/daemon.json && -s /etc/docker/daemon.json ]]; then
        warn "/etc/docker/daemon.json 已存在，保持现有配置不覆盖"
        return
    fi

    log "写入 Docker 镜像加速配置..."
    cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io",
    "https://mirror.baidubce.com",
    "https://dockerproxy.com"
  ]
}
EOF
}

start_docker_service() {
    log "启动 Docker 服务..."
    systemctl daemon-reload
    systemctl enable docker
    systemctl restart docker

    if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
        usermod -aG docker "${SUDO_USER}" || true
    fi
}

check_docker_ready() {
    command -v docker >/dev/null 2>&1 || die "未检测到 docker"
    docker version >/dev/null 2>&1 || die "docker 无法正常工作"
    docker compose version >/dev/null 2>&1 || die "未检测到 docker compose"
}

prepare_env_file() {
    if [[ -f "$ENV_FILE" ]]; then
        log "检测到现有 .env，保留现有配置"
        return
    fi

    if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        log "已根据 .env.example 创建 .env"
        return
    fi

    warn "未找到 .env.example，跳过 .env 自动创建"
}

compose_up() {
    [[ -f "$COMPOSE_FILE" ]] || die "未找到 compose 文件：$COMPOSE_FILE"

    prepare_env_file
    export PING_MONITOR_IMAGE="$IMAGE"
    mapfile -t compose_cmd < <(build_compose_cmd)

    log "拉取镜像：$PING_MONITOR_IMAGE"
    "${compose_cmd[@]}" pull ping-monitor mysql redis

    log "启动容器..."
    "${compose_cmd[@]}" up -d --no-build
}

verify_stack() {
    log "检查容器状态..."
    mapfile -t compose_cmd < <(build_compose_cmd)
    "${compose_cmd[@]}" ps
}

show_summary() {
    local compose_example="docker compose"
    if [[ -f "$ENV_FILE" ]]; then
        compose_example+=" --env-file $ENV_FILE"
    fi
    compose_example+=" -f $COMPOSE_FILE"

    printf '\n'
    printf '========================================\n'
    printf '部署完成\n'
    printf '========================================\n'
    printf '项目目录: %s\n' "$PROJECT_ROOT"
    printf '部署镜像: %s\n' "$IMAGE"
    printf '访问地址: http://<你的服务器IP>:8000\n'
    printf 'API 文档: http://<你的服务器IP>:8000/docs\n'
    printf '\n'
    printf '常用命令:\n'
    printf '  查看状态:\n'
    printf '    %s ps\n' "$compose_example"
    printf '  查看日志:\n'
    printf '    %s logs -f --tail=200\n' "$compose_example"
    printf '  停止服务:\n'
    printf '    %s down\n' "$compose_example"
    printf '========================================\n'
}

main() {
    require_root

    if [[ "$DEPLOY_ONLY" -ne 1 ]]; then
        install_docker_repo
        install_docker_packages
        configure_docker_daemon
        start_docker_service
    fi

    if [[ "$INSTALL_ONLY" -eq 1 ]]; then
        check_docker_ready
        log "Docker 安装完成"
        exit 0
    fi

    check_docker_ready
    compose_up
    verify_stack
    show_summary
}

main "$@"
