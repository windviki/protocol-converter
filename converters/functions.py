"""
Converter functions for special variables
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def func_sid(source_protocol: str, target_protocol: str, 
            source_json: Dict[str, Any], variables: Dict[str, Any]) -> str:
    """
    处理 __sid 特殊变量的转换函数
    Args:
        source_protocol: 源协议族
        target_protocol: 目标协议族
        source_json: 源JSON数据
        variables: 变量键值对
    Returns:
        转换后的值
    """
    logger.info(f"Converting __sid from {source_protocol} to {target_protocol}")
    
    # 根据源协议和目标协议的组合返回不同的值
    if source_protocol == "A" and target_protocol == "C":
        phone_type = variables.get("phone_type", "")
        if phone_type == "手机":
            return "PHONE_TYPE_MOBILE"
        elif phone_type == "座机":
            return "PHONE_TYPE_LANDLINE"
        else:
            return "PHONE_TYPE_UNKNOWN"
    
    elif source_protocol == "B" and target_protocol == "C":
        return "PHONE_TYPE_GENERIC"
    
    elif source_protocol == "A" and target_protocol == "B":
        return "PHONE_TYPE_LABEL"
    
    # 默认返回未知类型
    return "unknown"


def func_label(source_protocol: str, target_protocol: str, 
              source_json: Dict[str, Any], variables: Dict[str, Any]) -> str:
    """
    处理 __label 特殊变量的转换函数
    Args:
        source_protocol: 源协议族
        target_protocol: 目标协议族
        source_json: 源JSON数据
        variables: 变量键值对
    Returns:
        转换后的值
    """
    logger.info(f"Converting __label from {source_protocol} to {target_protocol}")
    
    # 根据协议组合返回不同的标签
    if target_protocol == "C":
        return "O"  # C协议通常使用O作为标签
    
    elif target_protocol == "B":
        return "B"  # B协议的标签
    
    # 默认返回通用标签
    return "GENERIC"


def func_priority(source_protocol: str, target_protocol: str, 
                 source_json: Dict[str, Any], variables: Dict[str, Any]) -> str:
    """
    处理 __priority 特殊变量的转换函数
    Args:
        source_protocol: 源协议族
        target_protocol: 目标协议族
        source_json: 源JSON数据
        variables: 变量键值对
    Returns:
        转换后的值
    """
    logger.info(f"Converting __priority from {source_protocol} to {target_protocol}")
    
    # 根据服务类型确定优先级
    service = source_json.get("domain", "")
    operation = source_json.get("action", "")
    
    if service == "telephone":
        if operation == "DIAL":
            return "HIGH"
        elif operation == "ANSWER":
            return "MEDIUM"
    
    # 默认优先级
    return "NORMAL"


def func_timestamp(source_protocol: str, target_protocol: str, 
                  source_json: Dict[str, Any], variables: Dict[str, Any]) -> str:
    """
    处理 __timestamp 特殊变量的转换函数
    Args:
        source_protocol: 源协议族
        target_protocol: 目标协议族
        source_json: 源JSON数据
        variables: 变量键值对
    Returns:
        转换后的值
    """
    import datetime
    
    logger.info(f"Converting __timestamp from {source_protocol} to {target_protocol}")
    
    # 返回当前时间戳
    now = datetime.datetime.now()
    
    if target_protocol == "C":
        return now.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        return now.strftime("%Y%m%d%H%M%S")


def func_session_id(source_protocol: str, target_protocol: str, 
                   source_json: Dict[str, Any], variables: Dict[str, Any]) -> str:
    """
    处理 __session_id 特殊变量的转换函数
    Args:
        source_protocol: 源协议族
        target_protocol: 目标协议族
        source_json: 源JSON数据
        variables: 变量键值对
    Returns:
        转换后的值
    """
    import uuid
    
    logger.info(f"Converting __session_id from {source_protocol} to {target_protocol}")
    
    # 生成会话ID
    if target_protocol == "C":
        return f"session_{uuid.uuid4().hex[:16]}"
    else:
        return uuid.uuid4().hex[:8]


def func_device_type(source_protocol: str, target_protocol: str, 
                    source_json: Dict[str, Any], variables: Dict[str, Any]) -> str:
    """
    处理 __device_type 特殊变量的转换函数
    Args:
        source_protocol: 源协议族
        target_protocol: 目标协议族
        source_json: 源JSON数据
        variables: 变量键值对
    Returns:
        转换后的值
    """
    logger.info(f"Converting __device_type from {source_protocol} to {target_protocol}")
    
    # 根据电话类型推断设备类型
    phone_type = variables.get("phone_type", "")
    
    if phone_type == "手机":
        return "MOBILE"
    elif phone_type == "座机":
        return "LANDLINE"
    elif phone_type == "软电话":
        return "SOFTPHONE"
    else:
        return "UNKNOWN"


# 转换函数字典，供系统使用
CONVERTER_FUNCTIONS = {
    "func_sid": func_sid,
    "func_label": func_label,
    "func_priority": func_priority,
    "func_timestamp": func_timestamp,
    "func_session_id": func_session_id,
    "func_device_type": func_device_type,
}


def get_converter_function(func_name: str):
    """
    获取转换函数
    Args:
        func_name: 函数名称
    Returns:
        转换函数或None
    """
    return CONVERTER_FUNCTIONS.get(func_name)


def register_converter_function(func_name: str, func: callable):
    """
    注册新的转换函数
    Args:
        func_name: 函数名称
        func: 转换函数
    """
    CONVERTER_FUNCTIONS[func_name] = func
    logger.info(f"Registered converter function: {func_name}")


def list_converter_functions() -> list:
    """
    列出所有可用的转换函数
    Returns:
        转换函数名称列表
    """
    return list(CONVERTER_FUNCTIONS.keys())