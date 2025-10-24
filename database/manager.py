"""
Database models and operations for protocol storage
"""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)


class ProtocolDatabase:
    """协议数据库管理类"""
    
    def __init__(self, db_path: str = "protocols.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        from models.models import Base
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # 使用SQLAlchemy创建表
        engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(engine)

        # 存储引擎和会话工厂
        self.engine = engine
        self.SessionLocal = sessionmaker(bind=engine)
    
    def save_protocol(self, protocol_id: str, protocol_family: str, 
                     template_content: Dict[str, Any], variables: List[str], 
                     special_variables: List[str]) -> bool:
        """
        保存协议到数据库
        Args:
            protocol_id: 协议ID
            protocol_family: 协议族
            template_content: 模板内容
            variables: 变量列表
            special_variables: 特殊变量列表
        Returns:
            是否保存成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO protocols 
                    (protocol_id, protocol_family, template_content, variables, special_variables)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    protocol_id,
                    protocol_family,
                    json.dumps(template_content, ensure_ascii=False),
                    json.dumps(variables, ensure_ascii=False),
                    json.dumps(special_variables, ensure_ascii=False)
                ))
                
                conn.commit()
                logger.info(f"Saved protocol: {protocol_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving protocol {protocol_id}: {e}")
            return False
    
    def get_protocol(self, protocol_id: str) -> Optional[Dict[str, Any]]:
        """
        获取协议
        Args:
            protocol_id: 协议ID
        Returns:
            协议数据或None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT protocol_id, protocol_family, template_content, variables, special_variables
                    FROM protocols WHERE protocol_id = ?
                ''', (protocol_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'protocol_id': row[0],
                        'protocol_family': row[1],
                        'template_content': json.loads(row[2]),
                        'variables': json.loads(row[3]),
                        'special_variables': json.loads(row[4])
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting protocol {protocol_id}: {e}")
            return None
    
    def get_protocols_by_family(self, protocol_family: str) -> List[Dict[str, Any]]:
        """
        获取指定协议族的所有协议
        Args:
            protocol_family: 协议族
        Returns:
            协议列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT protocol_id, protocol_family, template_content, variables, special_variables
                    FROM protocols WHERE protocol_family = ?
                ''', (protocol_family,))
                
                rows = cursor.fetchall()
                protocols = []
                for row in rows:
                    protocols.append({
                        'protocol_id': row[0],
                        'protocol_family': row[1],
                        'template_content': json.loads(row[2]),
                        'variables': json.loads(row[3]),
                        'special_variables': json.loads(row[4])
                    })
                
                return protocols
                
        except Exception as e:
            logger.error(f"Error getting protocols for family {protocol_family}: {e}")
            return []
    
    def get_all_protocols(self) -> List[Dict[str, Any]]:
        """
        获取所有协议
        Returns:
            所有协议列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT protocol_id, protocol_family, template_content, variables, special_variables
                    FROM protocols
                ''')
                
                rows = cursor.fetchall()
                protocols = []
                for row in rows:
                    protocols.append({
                        'protocol_id': row[0],
                        'protocol_family': row[1],
                        'template_content': json.loads(row[2]),
                        'variables': json.loads(row[3]),
                        'special_variables': json.loads(row[4])
                    })
                
                return protocols
                
        except Exception as e:
            logger.error(f"Error getting all protocols: {e}")
            return []
    
    def delete_protocol(self, protocol_id: str) -> bool:
        """
        删除协议
        Args:
            protocol_id: 协议ID
        Returns:
            是否删除成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM protocols WHERE protocol_id = ?', (protocol_id,))
                conn.commit()
                
                logger.info(f"Deleted protocol: {protocol_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting protocol {protocol_id}: {e}")
            return False
    
    def get_protocol_families(self) -> List[str]:
        """
        获取所有协议族
        Returns:
            协议族列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT DISTINCT protocol_family FROM protocols')
                rows = cursor.fetchall()
                
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting protocol families: {e}")
            return []
    
    def clear_database(self) -> bool:
        """
        清空数据库
        Returns:
            是否清空成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM protocols')
                conn.commit()
                
                logger.info("Database cleared")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False