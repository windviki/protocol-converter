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

    def _clean_template_for_matching(self, template: Any) -> Any:
        """
        清理模板中的Jinja2语法，只保留数据结构用于匹配

        Args:
            template: 模板内容

        Returns:
            清理后的模板内容
        """
        if isinstance(template, dict):
            cleaned = {}
            for key, value in template.items():
                cleaned_value = self._clean_template_for_matching(value)
                if cleaned_value is not None:  # 如果清理后不是None，则保留
                    cleaned[key] = cleaned_value
            return cleaned

        elif isinstance(template, list):
            cleaned_list = []
            for item in template:
                cleaned_item = self._clean_template_for_matching(item)
                if cleaned_item is not None:  # 保留非None项
                    cleaned_list.append(cleaned_item)
            return cleaned_list

        elif isinstance(template, str):
            # 如果是Jinja2注释，删除
            if template.strip().startswith('{#') and template.strip().endswith('#}'):
                return None
            # 如果是Jinja2变量或控制语句，保留原样（在匹配时会跳过）
            elif (template.strip().startswith('{{') or
                  template.strip().startswith('{%') or
                  template.strip().startswith('{#')):
                return template
            else:
                return template

        else:
            return template

    def _is_match(self, template: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """
        检查数据是否匹配模板
        Args:
            template: 模板内容
            data: 输入数据
        Returns:
            是否匹配
        """
        # 首先清理模板中的Jinja2注释
        cleaned_template = self._clean_template_for_matching(template)

        return self._recursive_match(cleaned_template, data)

    def _is_optional_field(self, field_name: str, template_value: Any) -> bool:
        """
        判断字段是否是可选的

        Args:
            field_name: 字段名
            template_value: 模板值

        Returns:
            是否是可选字段
        """
        # 根据字段名判断是否是可选的
        optional_keywords = ['context', 'metadata', 'session_info', 'processing']
        for keyword in optional_keywords:
            if keyword in field_name.lower():
                return True

        # 如果模板值是Jinja2变量，且包含默认值，则认为是可选的
        if isinstance(template_value, str) and 'default' in template_value:
            return True

        return False

    def _recursive_match(self, template: Any, data: Any) -> bool:
        """
        递归匹配模板和数据

        Args:
            template: 清理后的模板内容
            data: 输入数据

        Returns:
            是否匹配
        """
        # 如果模板是字典
        if isinstance(template, dict):
            if not isinstance(data, dict):
                return False

            # 检查模板中的所有字段在数据中都存在
            for key, template_value in template.items():
                # 如果模板值是Jinja2变量字符串，跳过匹配检查
                if isinstance(template_value, str) and (
                    template_value.strip().startswith('{{') or
                    template_value.strip().startswith('{%')):
                    continue

                # 检查字段是否存在
                if key not in data:
                    # 如果是可选字段，跳过检查
                    if self._is_optional_field(key, template_value):
                        continue
                    else:
                        return False

                # 递归检查嵌套结构
                if not self._recursive_match(template_value, data[key]):
                    return False

        # 如果模板是列表
        elif isinstance(template, list):
            if not isinstance(data, list):
                return False

            # 如果模板列表为空，数据列表也必须为空
            if len(template) == 0:
                return len(data) == 0

            # 如果模板列表不为空，检查结构匹配
            # 对于数组，只需要第一个元素的结构匹配即可
            if len(template) > 0 and len(data) > 0:
                template_first = template[0]
                data_first = data[0]
                if not self._recursive_match(template_first, data_first):
                    return False

        # 如果模板是字符串
        elif isinstance(template, str):
            # 如果模板值是Jinja2变量或控制语句，跳过匹配
            if (template.strip().startswith('{{') or
                template.strip().startswith('{%')):
                return True
            # 否则检查值是否相等
            else:
                return str(template) == str(data)

        return True