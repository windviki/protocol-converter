import json
import re
import os
from typing import Dict, List, Set, Any, Tuple
from jinja2 import Environment, FileSystemLoader, meta


def extract_variables_from_template(template_content: str) -> Tuple[Set[str], Set[str]]:
    """
    从Jinja2模板中提取变量
    
    Args:
        template_content: Jinja2模板内容
        
    Returns:
        Tuple[普通变量集合, 特殊变量集合]
    """
    env = Environment()
    parsed_content = env.parse(template_content)
    
    # 提取所有变量
    variables = meta.find_undeclared_variables(parsed_content)
    
    # 分离普通变量和特殊变量（以__开头的变量）
    normal_vars = set()
    special_vars = set()
    
    for var in variables:
        if var.startswith('__'):
            special_vars.add(var)
        else:
            normal_vars.add(var)
    
    return normal_vars, special_vars


def json_schema_match(schema: Dict[str, Any], data: Dict[str, Any]) -> bool:
    """
    检查JSON数据是否匹配schema结构
    
    Args:
        schema: 协议schema
        data: 要检查的JSON数据
        
    Returns:
        bool: 是否匹配
    """
    def _match_structure(schema_obj: Any, data_obj: Any) -> bool:
        # 如果schema_obj是字典
        if isinstance(schema_obj, dict):
            if not isinstance(data_obj, dict):
                return False
            
            # 检查schema中的所有key是否都在data中存在
            for key in schema_obj.keys():
                if key not in data_obj:
                    return False
                
                # 递归检查嵌套结构
                if not _match_structure(schema_obj[key], data_obj[key]):
                    return False
            
            return True
        
        # 如果schema_obj是列表
        elif isinstance(schema_obj, list):
            if not isinstance(data_obj, list):
                return False
            
            # 如果schema列表不为空，检查第一个元素的结构
            if schema_obj and data_obj:
                return _match_structure(schema_obj[0], data_obj[0])
            
            return True
        
        # 其他类型（字符串、数字等），直接匹配
        else:
            return isinstance(data_obj, type(schema_obj))
    
    return _match_structure(schema, data)


def extract_variables_from_json(schema: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据schema从JSON数据中提取变量值
    
    Args:
        schema: 协议schema
        data: JSON数据
        
    Returns:
        Dict[str, Any]: 变量键值对
    """
    variables = {}
    
    def _extract_recursive(schema_obj: Any, data_obj: Any, path: str = ""):
        if isinstance(schema_obj, dict) and isinstance(data_obj, dict):
            for key, schema_value in schema_obj.items():
                current_path = f"{path}.{key}" if path else key
                
                if key in data_obj:
                    data_value = data_obj[key]
                    
                    # 检查是否是Jinja2变量
                    if isinstance(schema_value, str) and schema_value.startswith('{{') and schema_value.endswith('}}'):
                        # 提取变量名
                        var_name = schema_value.strip('{{ }}').strip()
                        if var_name:
                            variables[var_name] = data_value
                    
                    # 递归处理嵌套结构
                    _extract_recursive(schema_value, data_value, current_path)
        
        elif isinstance(schema_obj, list) and isinstance(data_obj, list) and schema_obj and data_obj:
            # 处理列表中的第一个元素
            _extract_recursive(schema_obj[0], data_obj[0], f"{path}[0]")
    
    _extract_recursive(schema, data)
    return variables


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    加载JSON文件
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        Dict[str, Any]: JSON数据
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"加载JSON文件失败 {file_path}: {e}")


def scan_protocol_files(directory: str) -> List[str]:
    """
    扫描目录下的所有协议文件
    
    Args:
        directory: 目录路径
        
    Returns:
        List[str]: 协议文件路径列表
    """
    protocol_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                protocol_files.append(os.path.join(root, file))
    
    return sorted(protocol_files)


def parse_protocol_id(filename: str) -> Tuple[str, str]:
    """
    解析协议ID，提取协议族和子协议编号
    
    Args:
        filename: 文件名（如A-1.json）
        
    Returns:
        Tuple[str, str]: (协议族, 子协议编号)
    """
    basename = os.path.basename(filename)
    name_without_ext = os.path.splitext(basename)[0]
    
    if '-' in name_without_ext:
        family, protocol_num = name_without_ext.split('-', 1)
        return family, protocol_num
    else:
        return name_without_ext, "1"