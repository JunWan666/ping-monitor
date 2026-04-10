from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, select, text


def parse_args():
    parser = argparse.ArgumentParser(description="将 SQLite 数据迁移到 MySQL")
    parser.add_argument(
        "--sqlite-path",
        default="data/ping_monitor.db",
        help="SQLite 数据库文件路径，默认 data/ping_monitor.db",
    )
    parser.add_argument(
        "--mysql-url",
        required=True,
        help="MySQL SQLAlchemy URL，例如 mysql+pymysql://user:CHANGE_ME_IN_DOT_ENV@127.0.0.1:3306/ping_monitor?charset=utf8mb4",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="批量写入大小，默认 1000",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="迁移前清空目标表数据",
    )
    parser.add_argument(
        "--rebuild-statistics",
        action="store_true",
        help="迁移完成后重建小时和日级聚合统计",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    project_root = Path(__file__).resolve().parent.parent
    sqlite_path = (project_root / args.sqlite_path).resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"未找到 SQLite 数据库文件: {sqlite_path}")

    backend_dir = project_root / "backend"
    sys.path.insert(0, str(backend_dir))

    os.environ["DATABASE_URL"] = args.mysql_url
    from data_maintenance import DataMaintenance  # noqa: WPS433
    from database import Base  # noqa: WPS433

    source_engine = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    target_engine = create_engine(args.mysql_url, pool_pre_ping=True)

    Base.metadata.create_all(bind=target_engine)

    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)
    target_meta = MetaData()
    target_meta.reflect(bind=target_engine)

    ordered_tables = [table.name for table in Base.metadata.sorted_tables if table.name in source_meta.tables]

    with target_engine.begin() as target_conn:
        if args.truncate:
            for table_name in reversed(ordered_tables):
                target_conn.execute(text(f"DELETE FROM {table_name}"))

    total_rows = 0
    with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
        for table_name in ordered_tables:
            source_table: Table = source_meta.tables[table_name]
            target_table: Table = target_meta.tables[table_name]
            result = source_conn.execute(select(source_table)).mappings()

            batch = []
            table_rows = 0
            for row in result:
                batch.append(dict(row))
                if len(batch) >= args.batch_size:
                    target_conn.execute(target_table.insert(), batch)
                    table_rows += len(batch)
                    total_rows += len(batch)
                    batch = []

            if batch:
                target_conn.execute(target_table.insert(), batch)
                table_rows += len(batch)
                total_rows += len(batch)

            print(f"[完成] {table_name}: {table_rows} 行")

    if args.rebuild_statistics:
        print("[开始] 重建聚合统计...")
        DataMaintenance.aggregate_hourly_stats()
        DataMaintenance.aggregate_daily_stats()
        print("[完成] 聚合统计重建完成")

    print(f"迁移完成，总计 {total_rows} 行")


if __name__ == "__main__":
    main()
