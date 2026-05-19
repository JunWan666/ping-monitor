from __future__ import annotations

import math
import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import Base

BACKUP_HEADER = "-- Ping Monitor SQL Backup"
INSERT_BATCH_SIZE = 500


def _emit_progress(callback: Callable[[dict[str, Any]], None] | None, **payload: Any) -> None:
    if callback is not None:
        callback(payload)


def _quote_identifier(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def _quote_string(value: str, dialect_name: str) -> str:
    escaped = value.replace("'", "''")
    if dialect_name == "mysql":
        escaped = escaped.replace("\\", "\\\\")
    return f"'{escaped}'"


def _format_sql_value(value: Any, dialect_name: str) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value) if math.isfinite(value) else "NULL"
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return _quote_string(value.isoformat(sep=" ", timespec="microseconds"), dialect_name)
    if isinstance(value, date):
        return _quote_string(value.isoformat(), dialect_name)
    if isinstance(value, bytes):
        return f"X'{value.hex()}'"
    return _quote_string(str(value), dialect_name)


def _iter_table_rows(db: Session, table):
    statement = select(table)
    primary_keys = list(table.primary_key.columns)
    if primary_keys:
        statement = statement.order_by(*primary_keys)
    return db.execute(statement).mappings()


def _iter_insert_statements(db: Session, table, dialect_name: str) -> Iterator[str]:
    columns = list(table.columns)
    quoted_table = _quote_identifier(table.name)
    quoted_columns = ", ".join(_quote_identifier(column.name) for column in columns)
    prefix = f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES\n"
    batch: list[str] = []

    for row in _iter_table_rows(db, table):
        values = ", ".join(_format_sql_value(row[column.name], dialect_name) for column in columns)
        batch.append(f"({values})")
        if len(batch) >= INSERT_BATCH_SIZE:
            yield prefix + ",\n".join(batch) + ";\n"
            batch = []

    if batch:
        yield prefix + ",\n".join(batch) + ";\n"


def iter_database_backup_sql(db: Session) -> Iterator[str]:
    dialect_name = db.bind.dialect.name if db.bind is not None else "unknown"
    generated_at = datetime.now().isoformat(timespec="seconds")

    yield f"{BACKUP_HEADER}\n"
    yield f"-- Generated at: {generated_at}\n"
    yield f"-- Dialect: {dialect_name}\n\n"

    if dialect_name == "mysql":
        yield "SET FOREIGN_KEY_CHECKS=0;\n"
    elif dialect_name == "sqlite":
        yield "PRAGMA foreign_keys=OFF;\n"
    yield "\n"

    for table in reversed(Base.metadata.sorted_tables):
        yield f"DELETE FROM {_quote_identifier(table.name)};\n"
    yield "\n"

    for table in Base.metadata.sorted_tables:
        yield f"-- Table: {table.name}\n"
        has_rows = False
        for statement in _iter_insert_statements(db, table, dialect_name):
            has_rows = True
            yield statement
        if not has_rows:
            yield f"-- Empty table: {table.name}\n"
        yield "\n"

    if dialect_name == "mysql":
        yield "SET FOREIGN_KEY_CHECKS=1;\n"
    elif dialect_name == "sqlite":
        yield "PRAGMA foreign_keys=ON;\n"


def _split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    in_line_comment = False
    in_block_comment = False
    i = 0

    while i < len(sql_text):
        char = sql_text[i]
        next_char = sql_text[i + 1] if i + 1 < len(sql_text) else ""

        if in_line_comment:
            if char in "\r\n":
                in_line_comment = False
                buffer.append(char)
            i += 1
            continue

        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if quote is None:
            if char == "-" and next_char == "-":
                in_line_comment = True
                i += 2
                continue
            if char == "/" and next_char == "*":
                in_block_comment = True
                i += 2
                continue
            if char in ("'", '"', "`"):
                quote = char
                buffer.append(char)
                i += 1
                continue
            if char == ";":
                statement = "".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []
                i += 1
                continue
            buffer.append(char)
            i += 1
            continue

        buffer.append(char)
        if char == quote:
            if next_char == quote and quote in ("'", '"', "`"):
                buffer.append(next_char)
                i += 2
                continue
            quote = None
        i += 1

    statement = "".join(buffer).strip()
    if statement:
        statements.append(statement)
    return statements


def _normalize_statement(sql: str) -> str:
    return " ".join(sql.strip().split())


def _prepare_driver_sql(sql: str, dialect_name: str) -> str:
    if dialect_name == "mysql":
        return sql.replace("%", "%%")
    return sql


def _classify_statement(sql: str, allowed_tables: set[str]) -> tuple[str, str | None]:
    normalized = _normalize_statement(sql)
    upper = normalized.upper()

    if upper.startswith("SET FOREIGN_KEY_CHECKS") or upper.startswith("PRAGMA FOREIGN_KEYS"):
        return "control", None

    match = re.match(
        r"^(DELETE\s+FROM|INSERT\s+INTO)\s+[`\"]?([A-Za-z_][A-Za-z0-9_]*)[`\"]?",
        normalized,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("备份文件包含不支持的 SQL 语句，仅支持本系统导出的备份格式")

    table_name = match.group(2)
    if table_name not in allowed_tables:
        raise ValueError(f"备份文件包含未知数据表: {table_name}")
    return match.group(1).upper(), table_name


def import_database_backup_sql(
    db: Session,
    sql_text: str,
    *,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    _emit_progress(progress_callback, stage="validating", message="正在校验 SQL 备份文件")
    if BACKUP_HEADER not in sql_text[:2048]:
        raise ValueError("仅支持本系统导出的 SQL 备份文件")

    _emit_progress(progress_callback, stage="parsing", message="正在解析 SQL 语句")
    statements = _split_sql_statements(sql_text)
    if not statements:
        raise ValueError("SQL 备份文件为空")

    allowed_tables = {table.name for table in Base.metadata.sorted_tables}
    dialect_name = db.bind.dialect.name if db.bind is not None else "unknown"
    executed = 0
    skipped = 0
    total_statements = len(statements)
    classified_statements: list[tuple[str, str, str | None]] = []

    for index, statement in enumerate(statements, start=1):
        kind, table_name = _classify_statement(statement, allowed_tables)
        classified_statements.append((statement, kind, table_name))
        if index == total_statements or index % 200 == 0:
            _emit_progress(
                progress_callback,
                stage="parsing",
                message=f"已解析 {index}/{total_statements} 条 SQL 语句",
                parsed_statements=index,
                total_statements=total_statements,
            )

    _emit_progress(
        progress_callback,
        stage="executing",
        message=f"开始执行 {total_statements} 条 SQL 语句",
        executed_statements=0,
        skipped_statements=0,
        total_statements=total_statements,
    )

    connection = db.connection()

    try:
        current_table: str | None = None
        for index, (statement, kind, table_name) in enumerate(classified_statements, start=1):
            upper = _normalize_statement(statement).upper()

            if table_name and table_name != current_table:
                current_table = table_name
                _emit_progress(
                    progress_callback,
                    stage="executing",
                    message=f"正在导入数据表 {table_name}",
                    current_table=table_name,
                    executed_statements=executed,
                    skipped_statements=skipped,
                    total_statements=total_statements,
                )

            if kind == "control":
                if (upper.startswith("SET FOREIGN_KEY_CHECKS") and dialect_name != "mysql") or (
                    upper.startswith("PRAGMA FOREIGN_KEYS") and dialect_name != "sqlite"
                ):
                    skipped += 1
                    if index == total_statements or index % 50 == 0:
                        _emit_progress(
                            progress_callback,
                            stage="executing",
                            message=f"已执行 {index}/{total_statements} 条 SQL 语句",
                            current_table=current_table,
                            executed_statements=executed,
                            skipped_statements=skipped,
                            total_statements=total_statements,
                        )
                    continue

            connection.exec_driver_sql(_prepare_driver_sql(statement, dialect_name))
            executed += 1

            if index == total_statements or index % 50 == 0:
                _emit_progress(
                    progress_callback,
                    stage="executing",
                    message=f"已执行 {index}/{total_statements} 条 SQL 语句",
                    current_table=current_table,
                    executed_statements=executed,
                    skipped_statements=skipped,
                    total_statements=total_statements,
                )

        db.commit()
    except Exception:
        try:
            if dialect_name == "mysql":
                connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")
            elif dialect_name == "sqlite":
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        db.rollback()
        raise

    _emit_progress(progress_callback, stage="verifying", message="正在统计导入结果")

    table_counts = {
        table.name: db.execute(select(func.count()).select_from(table)).scalar_one()
        for table in Base.metadata.sorted_tables
    }

    _emit_progress(
        progress_callback,
        stage="completed",
        message="SQL 导入完成",
        executed_statements=executed,
        skipped_statements=skipped,
        total_statements=total_statements,
        table_counts=table_counts,
    )

    return {
        "total_statements": total_statements,
        "executed_statements": executed,
        "skipped_statements": skipped,
        "table_counts": table_counts,
    }
