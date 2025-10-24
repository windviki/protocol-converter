import json
import os
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from models.models import ProtocolFamily, Protocol
from database.connection import get_db_session
from utils.json_utils import (
    load_json_file, scan_protocol_files, parse_protocol_id,
    extract_variables_from_template, extract_variables_from_json
)


class ProtocolManager:
    """协议管理器"""
    
    def __init__(self):
        self.protocol_cache = {}  # 协议缓存
    
    def load_protocols_from_directory(self, directory: str) -> Dict[str, Any]:
        """
        从目录加载所有协议文件
        
        Args:
            directory: 协议文件目录
            
        Returns:
            Dict[str, Any]: 加载结果统计
        """
        if not os.path.exists(directory):
            raise Exception(f"目录不存在: {directory}")
        
        protocol_files = scan_protocol_files(directory)
        result = {
            'total_files': len(protocol_files),
            'loaded_files': 0,
            'failed_files': 0,
            'errors': []
        }
        
        for file_path in protocol_files:
            try:
                self._load_single_protocol(file_path)
                result['loaded_files'] += 1
                print(f"✓ 加载成功: {file_path}")
            except Exception as e:
                result['failed_files'] += 1
                error_msg = f"加载失败 {file_path}: {e}"
                result['errors'].append(error_msg)
                print(f"✗ {error_msg}")
        
        return result
    
    def _load_single_protocol(self, file_path: str):
        """
        加载单个协议文件
        
        Args:
            file_path: 协议文件路径
        """
        # 加载JSON文件
        protocol_data = load_json_file(file_path)
        
        # 解析协议ID
        family_name, protocol_num = parse_protocol_id(file_path)
        protocol_id = f"{family_name}-{protocol_num}"
        
        # 提取模板内容（原始JSON作为模板）
        template_content = json.dumps(protocol_data, ensure_ascii=False, indent=2)
        
        # 提取变量
        normal_vars, special_vars = extract_variables_from_template(template_content)
        
        # 创建schema（去除模板变量的结构）
        schema = self._create_schema_from_template(protocol_data)
        
        # 保存到数据库
        with get_db_session() as session:
            self._save_protocol_to_db(
                session=session,
                protocol_id=protocol_id,
                family_name=family_name,
                template_content=template_content,
                raw_schema=json.dumps(schema, ensure_ascii=False),
                normal_vars=list(normal_vars),
                special_vars=list(special_vars)
            )
        
        # 更新缓存
        self.protocol_cache[protocol_id] = {
            'family': family_name,
            'template': protocol_data,
            'schema': schema,
            'normal_vars': normal_vars,
            'special_vars': special_vars
        }
    
    def _create_schema_from_template(self, template_data: Any) -> Any:
        """
        从模板数据创建schema结构（去除Jinja2变量）
        
        Args:
            template_data: 模板数据
            
        Returns:
            Any: schema结构
        """
        if isinstance(template_data, dict):
            schema = {}
            for key, value in template_data.items():
                if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                    # 对于Jinja2变量，使用字符串类型作为schema
                    schema[key] = ""
                else:
                    schema[key] = self._create_schema_from_template(value)
            return schema
        elif isinstance(template_data, list):
            if template_data:
                return [self._create_schema_from_template(template_data[0])]
            return []
        else:
            # 对于基本类型，返回对应类型的默认值
            if isinstance(template_data, str):
                return ""
            elif isinstance(template_data, int):
                return 0
            elif isinstance(template_data, float):
                return 0.0
            elif isinstance(template_data, bool):
                return True
            else:
                return None
    
    def _save_protocol_to_db(self, session: Session, protocol_id: str, family_name: str,
                           template_content: str, raw_schema: str,
                           normal_vars: List[str], special_vars: List[str]):
        """
        保存协议到数据库
        
        Args:
            session: 数据库会话
            protocol_id: 协议ID
            family_name: 协议族名称
            template_content: 模板内容
            raw_schema: 原始schema
            normal_vars: 普通变量列表
            special_vars: 特殊变量列表
        """
        # 查找或创建协议族
        family = session.query(ProtocolFamily).filter_by(name=family_name).first()
        if not family:
            family = ProtocolFamily(name=family_name)
            session.add(family)
            session.flush()  # 获取ID
        
        # 检查协议是否已存在
        existing_protocol = session.query(Protocol).filter_by(protocol_id=protocol_id).first()
        if existing_protocol:
            # 更新现有协议
            existing_protocol.template_content = template_content
            existing_protocol.raw_schema = raw_schema
            existing_protocol.variables = json.dumps(normal_vars, ensure_ascii=False)
            existing_protocol.special_variables = json.dumps(special_vars, ensure_ascii=False)
        else:
            # 创建新协议
            protocol = Protocol(
                protocol_id=protocol_id,
                family_id=family.id,
                template_content=template_content,
                raw_schema=raw_schema,
                variables=json.dumps(normal_vars, ensure_ascii=False),
                special_variables=json.dumps(special_vars, ensure_ascii=False)
            )
            session.add(protocol)
    
    def get_protocol_by_id(self, protocol_id: str) -> Optional[Dict[str, Any]]:
        """
        根据协议ID获取协议信息
        
        Args:
            protocol_id: 协议ID
            
        Returns:
            Optional[Dict[str, Any]]: 协议信息
        """
        # 先从缓存中查找
        if protocol_id in self.protocol_cache:
            return self.protocol_cache[protocol_id]
        
        # 从数据库中查找
        with get_db_session() as session:
            protocol = session.query(Protocol).filter_by(protocol_id=protocol_id).first()
            if protocol:
                protocol_info = {
                    'family': protocol.family.name,
                    'template': json.loads(protocol.template_content),
                    'schema': json.loads(protocol.raw_schema),
                    'normal_vars': json.loads(protocol.variables) if protocol.variables else [],
                    'special_vars': json.loads(protocol.special_variables) if protocol.special_variables else []
                }
                # 更新缓存
                self.protocol_cache[protocol_id] = protocol_info
                return protocol_info
        
        return None
    
    def get_protocols_by_family(self, family_name: str) -> List[str]:
        """
        获取指定协议族的所有协议ID
        
        Args:
            family_name: 协议族名称
            
        Returns:
            List[str]: 协议ID列表
        """
        with get_db_session() as session:
            protocols = session.query(Protocol).join(ProtocolFamily).filter(
                ProtocolFamily.name == family_name
            ).all()
            return [p.protocol_id for p in protocols]
    
    def list_all_families(self) -> List[str]:
        """
        列出所有协议族
        
        Returns:
            List[str]: 协议族名称列表
        """
        with get_db_session() as session:
            families = session.query(ProtocolFamily).all()
            return [f.name for f in families]
    
    def clear_cache(self):
        """清空缓存"""
        self.protocol_cache.clear()
    
    def reload_cache(self):
        """重新加载缓存"""
        self.clear_cache()
        with get_db_session() as session:
            protocols = session.query(Protocol).all()
            for protocol in protocols:
                self.protocol_cache[protocol.protocol_id] = {
                    'family': protocol.family.name,
                    'template': json.loads(protocol.template_content),
                    'schema': json.loads(protocol.raw_schema),
                    'normal_vars': json.loads(protocol.variables) if protocol.variables else [],
                    'special_vars': json.loads(protocol.special_variables) if protocol.special_variables else []
                }