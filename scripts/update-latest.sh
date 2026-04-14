#!/usr/bin/env bash

set -Eeuo pipefail
trap 'printf "[ERROR] 脚本执行失败，第 %s 行命令: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

MODE="mysql-redis"
MIGRATE_SQLITE=0
TRUNCATE_MYSQL=0
SKIP_GIT_PULL=0
NO_BUILD=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"
BACKUP_DIR="$DATA_DIR/backups"
ENV_FILE="$PROJECT_ROOT/.env"

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

usage() {
    cat <<'EOF'
用法:
  ./scripts/update-latest.sh [--mode sqlite|mysql-redis] [--migrate-sqlite] [--truncate-mysql] [--skip-git-pull] [--no-build]

说明:
  --mode sqlite
      使用 SQLite 单库模式更新

  --mode mysql-redis
      使用 MySQL + Redis 模式更新，默认就是这个模式

  --migrate-sqlite
      在 mysql-redis 模式下，把 data/ping_monitor.db 迁移到 MySQL

  --truncate-mysql
      迁移前先清空 MySQL 目标表，通常只在首次迁移或重导时使用

  --skip-git-pull
      跳过 git pull，适合已经手动上传好代码的情况

  --no-build
      跳过 docker compose build，直接使用已有本地镜像或预构建远程镜像

示例:
  ./scripts/update-latest.sh
  ./scripts/update-latest.sh --mode mysql-redis --migrate-sqlite --truncate-mysql
  ./scripts/update-latest.sh --mode mysql-redis --no-build
  ./scripts/update-latest.sh --mode sqlite
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            [[ $# -ge 2 ]] || die "--mode 需要参数"
            MODE="$2"
            shift 2
            ;;
        --migrate-sqlite)
            MIGRATE_SQLITE=1
            shift
            ;;
        --truncate-mysql)
            TRUNCATE_MYSQL=1
            shift
            ;;
        --skip-git-pull)
            SKIP_GIT_PULL=1
            shift
            ;;
        --no-build)
            NO_BUILD=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "未知参数: $1"
            ;;
    esac
done

if [[ "$MODE" != "sqlite" && "$MODE" != "mysql-redis" ]]; then
    die "--mode 只能是 sqlite 或 mysql-redis"
fi

if [[ "$TRUNCATE_MYSQL" -eq 1 && "$MIGRATE_SQLITE" -ne 1 ]]; then
    die "--truncate-mysql 只能和 --migrate-sqlite 一起使用"
fi

command -v docker >/dev/null 2>&1 || die "未检测到 docker"
docker compose version >/dev/null 2>&1 || die "未检测到 docker compose"

if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
    warn "当前目录不是 git 仓库，跳过 git pull"
    SKIP_GIT_PULL=1
fi

if [[ "$MODE" == "mysql-redis" && ! -f "$ENV_FILE" ]]; then
    die "MySQL + Redis 模式需要先创建 $ENV_FILE。可先执行 cp .env.example .env"
fi

if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

compose_cmd=(
    docker compose
)

if [[ -f "$ENV_FILE" ]]; then
    compose_cmd+=(
        --env-file "$ENV_FILE"
    )
fi

compose_cmd+=(
    -f "$PROJECT_ROOT/docker/docker-compose.yml"
)

if [[ "$MODE" == "mysql-redis" ]]; then
    compose_cmd+=(
        -f "$PROJECT_ROOT/docker/docker-compose.mysql-redis.yml"
    )
fi

backup_sqlite() {
    local sqlite_file="$DATA_DIR/ping_monitor.db"

    if [[ ! -f "$sqlite_file" ]]; then
        warn "未找到 SQLite 文件: $sqlite_file，跳过备份"
        return
    fi

    mkdir -p "$BACKUP_DIR"
    local backup_file="$BACKUP_DIR/ping_monitor_$(date +%Y%m%d_%H%M%S).db"
    cp "$sqlite_file" "$backup_file"
    log "SQLite 备份完成: $backup_file"

    mapfile -t backups < <(ls -1t "$BACKUP_DIR"/ping_monitor_*.db 2>/dev/null || true)
    if [[ "${#backups[@]}" -gt 5 ]]; then
        for old_file in "${backups[@]:5}"; do
            rm -f "$old_file"
        done
        log "已清理旧备份，仅保留最近 5 份"
    fi
}

git_update() {
    if [[ "$SKIP_GIT_PULL" -eq 1 ]]; then
        warn "跳过 git pull"
        return
    fi

    log "更新代码..."
    git -C "$PROJECT_ROOT" pull --ff-only
}

stop_legacy_containers() {
    for container in ping-monitor ping-monitor-mysql ping-monitor-redis; do
        docker rm -f "$container" >/dev/null 2>&1 || true
    done
}

compose_down() {
    log "停止旧服务..."
    "${compose_cmd[@]}" down --remove-orphans || true
}

compose_pull_runtime_images() {
    if [[ "$MODE" == "mysql-redis" ]]; then
        log "拉取 MySQL / Redis 基础镜像..."
        "${compose_cmd[@]}" pull mysql redis || true
    fi

    if [[ "$NO_BUILD" -eq 1 && -n "${PING_MONITOR_IMAGE:-}" ]]; then
        log "拉取应用镜像: $PING_MONITOR_IMAGE"
        if ! "${compose_cmd[@]}" pull ping-monitor; then
            if docker image inspect "$PING_MONITOR_IMAGE" >/dev/null 2>&1; then
                warn "应用镜像拉取失败，但本地已存在镜像，继续使用本地镜像部署: $PING_MONITOR_IMAGE"
            else
                die "应用镜像拉取失败，且本地不存在镜像: $PING_MONITOR_IMAGE"
            fi
        fi
    fi
}

compose_up() {
    log "启动服务..."

    local up_args=(
        up -d --remove-orphans
    )
    if [[ "$NO_BUILD" -eq 0 ]]; then
        up_args+=(
            --build
        )
    fi

    "${compose_cmd[@]}" "${up_args[@]}"
}

verify_stack() {
    log "校验部署结果..."

    docker inspect ping-monitor >/dev/null 2>&1 || die "未找到 ping-monitor 容器"

    if [[ "$MODE" == "mysql-redis" ]]; then
        docker inspect ping-monitor-mysql >/dev/null 2>&1 || die "未找到 ping-monitor-mysql 容器"
        docker inspect ping-monitor-redis >/dev/null 2>&1 || die "未找到 ping-monitor-redis 容器"

        docker exec ping-monitor sh -lc 'getent hosts mysql >/dev/null' \
            || die "应用容器无法解析 mysql，请检查 Docker 网络"
        docker exec ping-monitor sh -lc 'getent hosts redis >/dev/null' \
            || die "应用容器无法解析 redis，请检查 Docker 网络"
    fi
}

run_sqlite_migration() {
    local sqlite_file="$DATA_DIR/ping_monitor.db"

    if [[ "$MODE" != "mysql-redis" ]]; then
        warn "当前不是 mysql-redis 模式，跳过迁移"
        return
    fi

    if [[ "$MIGRATE_SQLITE" -ne 1 ]]; then
        return
    fi

    if [[ ! -f "$sqlite_file" ]]; then
        die "你启用了 --migrate-sqlite，但未找到 $sqlite_file"
    fi

    local mysql_url="${DATABASE_URL:-mysql+pymysql://${MYSQL_USER:?set MYSQL_USER in .env}?charset=utf8mb4}"
    local migrate_args=(
        python /app/scripts/migrate_sqlite_to_mysql.py
        --sqlite-path data/ping_monitor.db
        --mysql-url "$mysql_url"
        --batch-size 5000
        --rebuild-statistics
    )

    if [[ "$TRUNCATE_MYSQL" -eq 1 ]]; then
        migrate_args+=(
            --truncate
        )
    fi

    log "准备执行 SQLite -> MySQL 迁移..."
    docker exec ping-monitor mkdir -p /app/scripts
    docker cp "$PROJECT_ROOT/scripts/migrate_sqlite_to_mysql.py" ping-monitor:/app/scripts/migrate_sqlite_to_mysql.py
    docker exec ping-monitor "${migrate_args[@]}"

    log "清理缓存版本..."
    docker exec ping-monitor python -c "import sys; sys.path.insert(0, '/app/backend'); from cache import cache_manager; cache_manager.invalidate_namespace('dashboard'); cache_manager.invalidate_namespace('databoard'); print('cache invalidated')"

    log "重启应用容器以加载最新数据状态..."
    docker restart ping-monitor >/dev/null
}

show_summary() {
    printf '\n'
    printf '========================================\n'
    printf '更新完成\n'
    printf '========================================\n'
    printf '部署模式: %s\n' "$MODE"
    printf '项目目录: %s\n' "$PROJECT_ROOT"
    printf '访问地址: http://<你的服务器IP>:8000\n'
    if [[ -n "${PING_MONITOR_IMAGE:-}" ]]; then
        printf '应用镜像: %s\n' "$PING_MONITOR_IMAGE"
    fi
    if [[ "$MODE" == "mysql-redis" ]]; then
        printf '\n'
        printf '数据库 / 缓存连接信息:\n'
        printf '  MySQL: %s:%s (user=%s, db=%s)\n' \
            "${MYSQL_BIND_HOST:-127.0.0.1}" "${MYSQL_PORT:-3307}" \
            "${MYSQL_USER:-ping_monitor}" "${MYSQL_DATABASE:-ping_monitor}"
        printf '  Redis: %s:%s (password required)\n' \
            "${REDIS_BIND_HOST:-127.0.0.1}" "${REDIS_PORT:-6380}"
        printf '  提示: 默认只绑定 127.0.0.1，更安全；如需公网直连，请显式改 *_BIND_HOST=0.0.0.0 并配置防火墙。\n'
    fi
    printf '\n'
    printf '常用命令:\n'
    printf '  查看日志:\n'
    printf '  %s logs -f --tail=100\n' "${compose_cmd[*]}"
    printf '\n'
    printf '  查看容器状态:\n'
    printf '  %s ps\n' "${compose_cmd[*]}"
    printf '\n'
    printf '当前服务状态:\n'
    "${compose_cmd[@]}" ps
    printf '========================================\n'
}

main() {
    log "项目目录: $PROJECT_ROOT"
    log "部署模式: $MODE"

    mkdir -p "$DATA_DIR"
    backup_sqlite
    git_update
    compose_pull_runtime_images
    compose_down
    stop_legacy_containers
    compose_up
    verify_stack
    run_sqlite_migration
    show_summary
}

main "$@"
