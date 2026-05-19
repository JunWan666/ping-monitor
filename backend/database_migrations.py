"""
数据库迁移模块
自动检测并更新数据库表结构
"""
import logging
from sqlalchemy import inspect, text
from database import engine, SessionLocal, Base

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """数据库迁移管理"""
    
    @staticmethod
    def get_column_names(table_name):
        """获取表的所有列名"""
        inspector = inspect(engine)
        try:
            columns = inspector.get_columns(table_name)
            return [col['name'] for col in columns]
        except Exception:
            return []
    
    @staticmethod
    def get_column_type(table_name, column_name):
        """获取列的类型信息"""
        inspector = inspect(engine)
        try:
            columns = inspector.get_columns(table_name)
            for col in columns:
                if col['name'] == column_name:
                    return col['type']
        except Exception:
            pass
        return None
    
    @staticmethod
    def column_exists(table_name, column_name):
        """检查列是否存在"""
        columns = DatabaseMigration.get_column_names(table_name)
        return column_name in columns
    
    @staticmethod
    def table_exists(table_name):
        """检查表是否存在"""
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    
    @staticmethod
    def get_sqlalchemy_type_sql(column_type):
        """将SQLAlchemy类型转换为当前数据库可执行的 SQL 类型"""
        type_str = str(column_type)
        upper_type = type_str.upper()
        
        # 处理常见类型
        if 'INTEGER' in upper_type:
            return 'INTEGER'
        elif 'VARCHAR' in upper_type:
            return type_str
        elif 'TEXT' in upper_type or 'STRING' in upper_type:
            return 'TEXT'
        elif 'FLOAT' in upper_type or 'NUMERIC' in upper_type:
            return 'REAL'
        elif 'BOOLEAN' in upper_type:
            return 'INTEGER'
        elif 'DATETIME' in upper_type:
            return 'DATETIME'
        else:
            return 'TEXT'  # 默认使用TEXT
    
    @staticmethod
    def get_column_default(column):
        """获取列的默认值"""
        if column.default is not None:
            if hasattr(column.default, 'arg'):
                default_value = column.default.arg
                if isinstance(default_value, str):
                    return f"DEFAULT '{default_value}'"
                elif isinstance(default_value, bool):
                    return f"DEFAULT {1 if default_value else 0}"
                elif default_value is None:
                    return "DEFAULT NULL"
                else:
                    return f"DEFAULT {default_value}"
        return ""
    
    @staticmethod
    def add_column_if_not_exists(db, table_name, column_name, column_definition):
        """如果列不存在则添加"""
        if not DatabaseMigration.column_exists(table_name, column_name):
            try:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                db.execute(text(sql))
                db.commit()
                logger.info(f"✅ 已添加字段: {table_name}.{column_name}")
                return True
            except Exception as e:
                logger.error(f"❌ 添加字段失败: {table_name}.{column_name}, 错误: {e}")
                db.rollback()
                return False
        else:
            logger.debug(f"⏭️  字段已存在: {table_name}.{column_name}")
            return False
    
    @staticmethod
    def auto_sync_table_structure():
        """自动同步表结构：比对Model定义和数据库实际结构"""
        db = SessionLocal()
        migrations_executed = []
        
        try:
            # 遍历所有Model
            for mapper in Base.registry.mappers:
                model_class = mapper.class_
                table_name = mapper.mapped_table.name
                
                # 检查表是否存在
                if not DatabaseMigration.table_exists(table_name):
                    logger.warning(f"⚠️  表不存在: {table_name}, 请运行init_db()创建")
                    continue
                
                # 获取现有的列
                existing_columns = DatabaseMigration.get_column_names(table_name)
                
                # 遍历Model中定义的列
                for column in mapper.mapped_table.columns:
                    column_name = column.name
                    
                    # 如果列不存在，则添加
                    if column_name not in existing_columns:
                        # 构建列定义
                        column_type = DatabaseMigration.get_sqlalchemy_type_sql(column.type)
                        default_value = DatabaseMigration.get_column_default(column)
                        nullable = "" if column.nullable else "NOT NULL"
                        
                        column_definition = f"{column_type} {default_value} {nullable}".strip()
                        
                        # 添加列
                        if DatabaseMigration.add_column_if_not_exists(db, table_name, column_name, column_definition):
                            migrations_executed.append(f"{table_name}.{column_name}")
            
            return migrations_executed
            
        except Exception as e:
            logger.error(f"❌ 自动同步表结构失败: {e}")
            db.rollback()
            return migrations_executed
        finally:
            db.close()
    
    @staticmethod
    def run_migrations():
        """执行所有数据库迁移"""
        try:
            logger.info("🔄 开始检查数据库表结构...")
            
            # 自动同步表结构
            migrations_executed = DatabaseMigration.auto_sync_table_structure()
            
            # 迁移总结
            if migrations_executed:
                logger.info(f"✅ 数据库迁移完成，共执行 {len(migrations_executed)} 个迁移:")
                for migration in migrations_executed:
                    logger.info(f"   - {migration}")
            else:
                logger.info("✅ 数据库表结构已是最新，无需迁移")
            
        except Exception as e:
            logger.error(f"❌ 数据库迁移失败: {e}")

if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 执行迁移
    DatabaseMigration.run_migrations()
