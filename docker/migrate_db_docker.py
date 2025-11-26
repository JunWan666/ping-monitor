"""Docker环境数据库迁移脚本：添加新字段"""
import sqlite3
from pathlib import Path
import os

# Docker环境中的数据库路径
if os.getenv('DB_PATH'):
    DB_PATH = os.getenv('DB_PATH')
else:
    # Docker默认路径
    DB_PATH = '/app/data/ping_monitor.db'

print(f"数据库路径: {DB_PATH}")

# 检查数据库文件是否存在
if not os.path.exists(DB_PATH):
    print(f"❌ 数据库文件不存在: {DB_PATH}")
    print("提示: 请确保数据目录已正确挂载到容器")
    exit(1)

# 连接数据库
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("开始迁移数据库...")

try:
    # 检查 system_config 表是否存在 notification_mode 字段
    cursor.execute("PRAGMA table_info(system_config)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'notification_mode' not in columns:
        print("添加 notification_mode 字段到 system_config 表...")
        cursor.execute("""
            ALTER TABLE system_config 
            ADD COLUMN notification_mode TEXT DEFAULT 'status_change'
        """)
        print("✅ notification_mode 字段添加成功")
    else:
        print("✓ notification_mode 字段已存在")
    
    # 检查 hosts 表是否存在 last_status 字段
    cursor.execute("PRAGMA table_info(hosts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'last_status' not in columns:
        print("添加 last_status 字段到 hosts 表...")
        cursor.execute("""
            ALTER TABLE hosts 
            ADD COLUMN last_status TEXT
        """)
        print("✅ last_status 字段添加成功")
    else:
        print("✓ last_status 字段已存在")
    
    conn.commit()
    print("\n✅ 数据库迁移完成！")
    print("提示: 现在可以重启服务使用新功能了")
    
except Exception as e:
    print(f"\n❌ 数据库迁移失败: {e}")
    conn.rollback()
    exit(1)
finally:
    conn.close()
