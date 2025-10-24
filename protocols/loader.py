"""
Protocol loader for reading and storing protocol templates
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import re

from ..core.converter import ProtocolConverter, ProtocolTemplate
from ..database.manager import ProtocolDatabase

logger = logging.getLogger(__name__)


class ProtocolLoader:
    """协议加载器"""
    
    def __init__(self, db_path: str = "protocols.db"):
        self.db = ProtocolDatabase(db_path)
        self.converter = ProtocolConverter()
    
    def load_from_directory(self, directory: str) -> int:
        """
        从目录加载所有协议文件
        Args:
            directory: 协议文件目录
        Returns:
            加载的协议数量
        """
        if not os.path.exists(directory):
            logger.error(f"Directory not found: {directory}")
            return 0
        
        loaded_count = 0
        protocol_files = self._find_protocol_files(directory)
        
        for file_path in protocol_files:
            try:
                if self._load_protocol_file(file_path):
                    loaded_count += 1
            except Exception as e:
                logger.error(f"Error loading protocol file {file_path}: {e}")
        
        logger.info(f"Loaded {loaded_count} protocols from {directory}")
        return loaded_count
    
    def load_from_file(self, file_path: str) -> bool:
        """
        从单个文件加载协议
        Args:
            file_path: 协议文件路径
        Returns:
            是否加载成功
        """
        return self._load_protocol_file(file_path)
    
    def _find_protocol_files(self, directory: str) -> List[str]:
        """查找所有协议文件"""
        protocol_files = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    protocol_files.append(os.path.join(root, file))
        
        return protocol_files
    
    def _load_protocol_file(self, file_path: str) -> bool:
        """
        加载单个协议文件
        Args:
            file_path: 协议文件路径
        Returns:
            是否加载成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_content = json.load(f)
            
            # 从文件名提取协议ID和协议族
            filename = os.path.basename(file_path)
            protocol_id = os.path.splitext(filename)[0]
            
            # 解析协议族（例如 A-1.json -> 协议族为 A）
            protocol_family = self._extract_protocol_family(protocol_id)
            
            if not protocol_family:
                logger.error(f"Cannot extract protocol family from filename: {filename}")
                return False
            
            # 提取模板中的变量
            variables = self._extract_template_variables(template_content)
            special_variables = self._extract_special_variables(template_content)
            
            # 保存到数据库
            success = self.db.save_protocol(
                protocol_id=protocol_id,
                protocol_family=protocol_family,
                template_content=template_content,
                variables=variables,
                special_variables=special_variables
            )
            
            if success:
                # 同时加载到转换器中
                self.converter.load_protocol(protocol_id, protocol_family, template_content)
                logger.info(f"Loaded protocol: {protocol_id} from {file_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error loading protocol file {file_path}: {e}")
            return False
    
    def _extract_protocol_family(self, protocol_id: str) -> Optional[str]:
        """
        从协议ID中提取协议族
        Args:
            protocol_id: 协议ID（如 A-1, B-2, C-3）
        Returns:
            协议族名称或None
        """
        # 匹配格式：字母-数字（如 A-1, B-2, C-3）
        match = re.match(r'^([A-Za-z]+)-\d+__', protocol_id)
        if match:
            return match.group(1)
        
        # 如果不匹配标准格式，尝试其他格式
        parts = protocol_id.split('-')
        if len(parts) >= 2:
            return parts[0]
        
        return None
    
    def _extract_template_variables(self, template: Dict[str, Any]) -> List[str]:
        """提取模板中的普通变量"""
        variables = set()
        self._extract_variables_from_dict(template, variables)
        return [v for v in variables if not v.startswith('__')]
    
    def _extract_special_variables(self, template: Dict[str, Any]) -> List[str]:
        """提取模板中的特殊变量"""
        variables = set()
        self._extract_variables_from_dict(template, variables)
        return [v for v in variables if v.startswith('__')]
    
    def _extract_variables_from_dict(self, data: Dict[str, Any], variables: set):
        """从字典中提取变量"""
        for value in data.values():
            if isinstance(value, str):
                # 使用正则表达式匹配Jinja2变量
                matches = re.findall(r'\{\{\s*([^}]+)\s*\}\}', value)
                for match in matches:
                    var_name = match.strip()
                    variables.add(var_name)
            elif isinstance(value, dict):
                self._extract_variables_from_dict(value, variables)
            elif isinstance(value, list):
                self._extract_variables_from_list(value, variables)
    
    def _extract_variables_from_list(self, data: List[Any], variables: set):
        """从列表中提取变量"""
        for item in data:
            if isinstance(item, str):
                matches = re.findall(r'\{\{\s*([^}]+)\s*\}\}', item)
                for match in matches:
                    var_name = match.strip()
                    variables.add(var_name)
            elif isinstance(item, dict):
                self._extract_variables_from_dict(item, variables)
            elif isinstance(item, list):
                self._extract_variables_from_list(item, variables)
    
    def get_loaded_protocols(self) -> List[str]:
        """获取已加载的协议列表"""
        protocols = self.db.get_all_protocols()
        return [p['protocol_id'] for p in protocols]
    
    def get_protocol_families(self) -> List[str]:
        """获取协议族列表"""
        return self.db.get_protocol_families()
    
    def reload_database_to_converter(self):
        """重新加载数据库中的协议到转换器"""
        protocols = self.db.get_all_protocols()
        
        # 清空转换器中的协议
        self.converter.matcher.protocols.clear()
        
        # 重新加载
        for protocol_data in protocols:
            self.converter.load_protocol(
                protocol_data['protocol_id'],
                protocol_data['protocol_family'],
                protocol_data['template_content']
            )
        
        logger.info(f"Reloaded {len(protocols)} protocols to converter")
    
    def get_converter(self) -> ProtocolConverter:
        """获取转换器实例"""
        return self.converter