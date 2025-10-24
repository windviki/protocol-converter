"""
Converter functions for special variables
"""

import logging
from typing import Dict, Any, Optional
import sys
import os

# 添加项目路径以导入ConversionContext
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.types import ConversionContext
except ImportError:
    # 如果导入失败，定义一个简单的替代
    class ConversionContext:
        pass

logger = logging.getLogger(__name__)


def func_sid(context: ConversionContext) -> str:
    """
    处理 __sid 特殊变量的转换函数
    Args:
        context: 转换上下文
    Returns:
        转换后的值
    """
    logger.info(f"Converting __sid from {context.source_protocol} to {context.target_protocol}")

    # 根据源协议和目标协议的组合返回不同的值
    if context.source_protocol == "A" and context.target_protocol == "C":
        phone_type = context.get_variable("phone_type", "")
        if phone_type == "手机":
            return "PHONE_TYPE_MOBILE"
        elif phone_type == "座机":
            return "PHONE_TYPE_LANDLINE"
        else:
            return "PHONE_TYPE_UNKNOWN"

    elif context.source_protocol == "B" and context.target_protocol == "C":
        return "PHONE_TYPE_GENERIC"

    elif context.source_protocol == "A" and context.target_protocol == "B":
        return "PHONE_TYPE_LABEL"

    # 默认返回未知类型
    return "unknown"


def func_label(context: ConversionContext) -> str:
    """
    处理 __label 特殊变量的转换函数
    Args:
        context: 转换上下文
    Returns:
        转换后的值
    """
    logger.info(f"Converting __label from {context.source_protocol} to {context.target_protocol}")

    # 根据协议组合返回不同的标签
    if context.target_protocol == "C":
        return "O"  # C协议通常使用O作为标签

    elif context.target_protocol == "B":
        return "B"  # B协议的标签

    # 默认返回通用标签
    return "GENERIC"


def func_priority(context: ConversionContext) -> str:
    """
    处理 __priority 特殊变量的转换函数
    Args:
        context: 转换上下文
    Returns:
        转换后的值
    """
    logger.info(f"Converting __priority from {context.source_protocol} to {context.target_protocol}")

    # 根据服务类型确定优先级
    service = context.get_source_field("domain", "")
    operation = context.get_source_field("action", "")

    if service == "telephone":
        if operation == "DIAL":
            return "HIGH"
        elif operation == "ANSWER":
            return "MEDIUM"

    # 默认优先级
    return "NORMAL"


def func_timestamp(context: ConversionContext) -> str:
    """
    处理 __timestamp 特殊变量的转换函数
    Args:
        context: 转换上下文
    Returns:
        转换后的值
    """
    import datetime

    logger.info(f"Converting __timestamp from {context.source_protocol} to {context.target_protocol}")

    # 返回当前时间戳（使用context中的时间戳以保持一致性）
    if context.timestamp:
        try:
            parsed_time = datetime.datetime.fromisoformat(context.timestamp.replace('T', ' ').replace('-', ' ').replace(':', ' '))
            if context.target_protocol == "C":
                return parsed_time.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                return parsed_time.strftime("%Y%m%d%H%M%S")
        except:
            pass

    # 如果解析失败，返回当前时间
    now = datetime.datetime.now()
    if context.target_protocol == "C":
        return now.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        return now.strftime("%Y%m%d%H%M%S")


def func_session_id(context: ConversionContext) -> str:
    """
    处理 __session_id 特殊变量的转换函数
    Args:
        context: 转换上下文
    Returns:
        转换后的值
    """
    import uuid

    logger.info(f"Converting __session_id from {context.source_protocol} to {context.target_protocol}")

    # 如果在数组中，使用索引和转换ID生成不同的session_id
    if context.is_array_context():
        progress_info = context.get_progress_info()
        base_id = f"item{context.array_index}_conv{context.conversion_id[:8]}"
        if context.target_protocol == "C":
            return f"session_{base_id}_{uuid.uuid4().hex[:8]}"
        else:
            return f"{base_id}_{uuid.uuid4().hex[:6]}"

    # 生成会话ID（基于转换ID）
    if context.target_protocol == "C":
        return f"session_conv_{context.conversion_id[:12]}"
    else:
        return f"conv_{context.conversion_id[:8]}"


def func_session_id_v2(context: ConversionContext) -> str:
    """
    新版本的session_id转换函数，充分利用上下文信息
    这个函数演示了如何使用新的上下文机制
    """
    import uuid

    logger.info(f"Converting __session_id_v2 from {context.source_protocol} to {context.target_protocol}")

    # 构建详细的基础信息
    info_parts = []

    # 协议信息
    info_parts.append(f"{context.source_protocol}_to_{context.target_protocol}")

    # 协议ID信息
    if context.source_protocol_id:
        info_parts.append(f"src_{context.source_protocol_id}")
    if context.target_protocol_id:
        info_parts.append(f"tgt_{context.target_protocol_id}")

    # 数组信息
    if context.is_array_context():
        array_info = f"idx{context.array_index}_total{context.array_total}"
        if context.array_path:
            array_info = f"{context.array_path}_{array_info}"
        info_parts.append(array_info)

        # 进度信息
        progress = context.get_progress_info()
        info_parts.append(f"progress{progress['percentage']:.0f}%")

    # 路径信息
    if context.current_path:
        info_parts.append(f"path_{context.current_path.replace('.', '_')}")

    # 组合所有信息
    base_info = "_".join(info_parts)

    # 生成唯一ID
    unique_id = uuid.uuid4().hex[:12]

    if context.target_protocol == "C":
        return f"session_{base_info}_{unique_id}"
    else:
        return f"{base_info}_{unique_id}"


def func_array_index(context: ConversionContext) -> str:
    """
    返回当前数组元素的索引
    如果不在数组中，返回-1
    """
    return str(context.array_index) if context.is_array_context() else "-1"


def func_array_total(context: ConversionContext) -> str:
    """
    返回当前数组的总长度
    如果不在数组中，返回0
    """
    return str(context.array_total) if context.array_total is not None else "0"


def func_progress(context: ConversionContext) -> str:
    """
    返回当前处理进度信息
    """
    if context.is_array_context():
        progress = context.get_progress_info()
        return f"{progress['current']}/{progress['total']} ({progress['percentage']:.1f}%)"
    else:
        return "1/1 (100.0%)"


def func_is_last_item(context: ConversionContext) -> str:
    """
    返回是否为最后一个项目
    """
    return "true" if context.is_last_item else "false"


def func_conversion_id(context: ConversionContext) -> str:
    """
    返回转换会话ID
    """
    return context.conversion_id or "unknown"


def func_current_path(context: ConversionContext) -> str:
    """
    返回当前渲染路径
    """
    return context.current_path or "root"


def func_source_protocol(context: ConversionContext) -> str:
    """
    返回源协议名称
    """
    return context.source_protocol or "unknown"


def func_target_protocol(context: ConversionContext) -> str:
    """
    返回目标协议名称
    """
    return context.target_protocol or "unknown"


def func_render_depth(context: ConversionContext) -> str:
    """
    返回当前渲染深度
    """
    return str(context.render_depth)


def func_parent_path(context: ConversionContext) -> str:
    """
    返回父级路径
    """
    return context.parent_path or "root"


def func_device_type(context: ConversionContext) -> str:
    """
    处理 __device_type 特殊变量的转换函数
    Args:
        context: 转换上下文
    Returns:
        转换后的值
    """
    logger.info(f"Converting __device_type from {context.source_protocol} to {context.target_protocol}")

    # 根据电话类型推断设备类型
    phone_type = context.get_variable("phone_type", "")

    if phone_type == "手机":
        return "MOBILE"
    elif phone_type == "座机":
        return "LANDLINE"
    elif phone_type == "软电话":
        return "SOFTPHONE"
    else:
        return "UNKNOWN"


def func_primary_road(context: ConversionContext) -> str:
    """
    从目的地地址中提取主要道路名称
    """
    destination = context.get_variable("destination", "")
    if not destination:
        return ""

    # 简单的地址解析逻辑：寻找 "路" 前面的内容
    if "路" in destination:
        # 寻找第一个路名
        import re
        match = re.search(r'([^路，,]+路)', destination)
        if match:
            return match.group(1)

    # 如果没有找到，返回前半部分
    if "交叉口" in destination:
        parts = destination.split("交叉口")
        if len(parts) >= 2:
            return parts[0].strip()

    # 默认返回整个地址
    return destination


def func_secondary_road(context: ConversionContext) -> str:
    """
    从目的地地址中提取次要道路名称
    """
    destination = context.get_variable("destination", "")
    if not destination:
        return ""

    # 寻找第二个路名
    if "路" in destination:
        import re
        matches = re.findall(r'([^路，,]+路)', destination)
        if len(matches) >= 2:
            return matches[1]

    # 如果有交叉口标识，尝试提取第二部分
    if "交叉口" in destination:
        parts = destination.split("交叉口")
        if len(parts) >= 2:
            # 从第二部分中提取路名
            second_part = parts[1].strip()
            if "路" in second_part:
                import re
                match = re.search(r'([^路，,]+路)', second_part)
                if match:
                    return match.group(1)

    return ""


def func_full_address(context: ConversionContext) -> str:
    """
    构建完整地址
    """
    city = context.get_variable("city", "上海")
    district = context.get_variable("district", "")
    destination = context.get_variable("destination", "")

    address_parts = []
    if city:
        address_parts.append(city)
    if district:
        address_parts.append(district)
    if destination:
        address_parts.append(destination)

    return "".join(address_parts)


# 转换函数字典，供系统使用
CONVERTER_FUNCTIONS = {
    "func_sid": func_sid,
    "func_label": func_label,
    "func_priority": func_priority,
    "func_timestamp": func_timestamp,
    "func_session_id": func_session_id,
    "func_session_id_v2": func_session_id_v2,
    "func_array_index": func_array_index,
    "func_array_total": func_array_total,
    "func_progress": func_progress,
    "func_is_last_item": func_is_last_item,
    "func_conversion_id": func_conversion_id,
    "func_current_path": func_current_path,
    "func_source_protocol": func_source_protocol,
    "func_target_protocol": func_target_protocol,
    "func_render_depth": func_render_depth,
    "func_parent_path": func_parent_path,
    "func_device_type": func_device_type,
    "func_primary_road": func_primary_road,
    "func_secondary_road": func_secondary_road,
    "func_full_address": func_full_address,
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