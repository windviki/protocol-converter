"""
Protocol matcher module for finding matching templates
"""

import logging
from typing import Dict, Any, Optional

from models.types import ProtocolTemplate

logger = logging.getLogger(__name__)


class ProtocolMatcher:
    """协议匹配器"""

    def __init__(self):
        self.protocols: Dict[str, ProtocolTemplate] = {}

    def add_protocol(self, protocol: ProtocolTemplate):
        """添加协议模板"""
        self.protocols[protocol.protocol_id] = protocol

    def match_protocol(self, protocol_family: str, json_data: Dict[str, Any]) -> Optional[str]:
        """
        匹配协议模板
        Args:
            protocol_family: 协议族名称
            json_data: 输入的JSON数据
        Returns:
            匹配的协议ID，如果没有匹配则返回None
        """
        # 获取该协议族的所有协议
        family_protocols = {pid: p for pid, p in self.protocols.items()
                          if p.protocol_family == protocol_family}

        for protocol_id, protocol in family_protocols.items():
            if self._is_match(protocol.template_content, json_data):
                logger.info(f"Matched protocol: {protocol_id}")
                return protocol_id

        return None

    def _is_match(self, template: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """
        检查数据是否匹配模板
        Args:
            template: 模板内容
            data: 输入数据
        Returns:
            是否匹配
        """
        # 检查所有模板中的字段在数据中都存在
        for key, template_value in template.items():
            # 如果模板值是Jinja2变量字符串，跳过匹配检查
            if isinstance(template_value, str) and template_value.strip().startswith('{{') and template_value.strip().endswith('}}'):
                continue

            if key not in data:
                return False

            # 递归检查嵌套结构
            if isinstance(template_value, dict) and isinstance(data[key], dict):
                if not self._is_match(template_value, data[key]):
                    return False
            elif isinstance(template_value, list) and isinstance(data[key], list):
                # 对于数组，检查每个元素的结构
                if len(template_value) > 0 and len(data[key]) > 0:
                    if isinstance(template_value[0], dict) and isinstance(data[key][0], dict):
                        if not self._is_match(template_value[0], data[key][0]):
                            return False
                    # 如果模板值是字符串且包含Jinja2变量，跳过匹配检查
                    elif isinstance(template_value[0], str) and template_value[0].strip().startswith('{{') and template_value[0].strip().endswith('}}'):
                        continue

        return True