"""
Main protocol converter module
"""

import json
import logging
from typing import Dict, List, Any, Optional
from jinja2 import meta

from models.types import ProtocolTemplate, ConversionResult

logger = logging.getLogger(__name__)
from .matcher import ProtocolMatcher
from .extractor import VariableExtractor, ArrayMarkerParser
from .renderer import TemplateRenderer

logger = logging.getLogger(__name__)


class ProtocolConverter:
    """协议转换器主类"""

    def __init__(self, converter_functions: Dict[str, callable] = None):
        self.matcher = ProtocolMatcher()
        self.extractor = VariableExtractor()
        self.converter_functions = converter_functions or {}
        self.renderer = TemplateRenderer(self.converter_functions)

    def load_protocol(self, protocol_id: str, protocol_family: str,
                   template_content: Dict[str, Any] = None, template: ProtocolTemplate = None):
        """加载协议模板"""
        if template is not None:
            # 使用提供的ProtocolTemplate对象
            protocol = template
        else:
            # 从template_content创建ProtocolTemplate
            if template_content is None:
                raise ValueError("Either template_content or template must be provided")

            # 提取模板中的变量
            variables = self._extract_template_variables(template_content)
            special_variables = self._extract_special_variables(template_content)

            # 解析数组标记
            array_markers = ArrayMarkerParser.parse_array_markers(template_content)

            protocol = ProtocolTemplate(
                protocol_id=protocol_id,
                protocol_family=protocol_family,
                template_content=template_content,
                variables=variables,
                special_variables=special_variables,
                array_markers=array_markers
            )

        self.matcher.add_protocol(protocol)
        logger.info(f"Loaded protocol: {protocol_id} with {len(protocol.array_markers)} array markers")

    def convert(self, source_protocol: str, target_protocol: str,
                source_json: Dict[str, Any]) -> ConversionResult:
        """
        转换协议
        Args:
            source_protocol: 源协议族
            target_protocol: 目标协议族
            source_json: 源JSON数据
        Returns:
            转换结果
        """
        try:
            # 1. 匹配源协议
            matched_protocol_id = self.matcher.match_protocol(source_protocol, source_json)
            if not matched_protocol_id:
                return ConversionResult(
                    success=False,
                    error=f"No matching protocol found for {source_protocol}"
                )

            # 2. 获取源协议模板
            source_protocol_template = self.matcher.protocols[matched_protocol_id]

            # 3. 提取变量
            variables = self.extractor.extract_variables(
                source_protocol_template.template_content,
                source_json,
                source_protocol_template.array_markers
            )

            # 4. 查找目标协议模板
            target_protocol_template = self._find_target_protocol(target_protocol, matched_protocol_id)
            if not target_protocol_template:
                return ConversionResult(
                    success=False,
                    error=f"No corresponding target protocol found for {matched_protocol_id}"
                )

            # 5. 渲染目标协议
            result = self.renderer.render(
                target_protocol_template.template_content,
                variables,
                source_protocol,
                target_protocol,
                source_json,
                target_protocol_template.array_markers,
                source_protocol_id=matched_protocol_id,
                target_protocol_id=target_protocol_template.protocol_id
            )

            return ConversionResult(
                success=True,
                result=result,
                matched_protocol=matched_protocol_id,
                variables=variables
            )

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return ConversionResult(
                success=False,
                error=str(e)
            )

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
                # 检查字符串是否包含Jinja2模板语法
                if '{{' in value or '{%' in value or '{#' in value:
                    try:
                        # 使用Jinja2解析变量
                        ast = self.renderer.env.parse(value)
                        undeclared_vars = meta.find_undeclared_variables(ast)
                        # 只添加非特殊变量
                        for var in undeclared_vars:
                            if not var.startswith('__'):
                                variables.add(var)
                    except Exception as e:
                        # 如果解析失败，尝试使用正则表达式提取变量
                        logger.debug(f"Jinja2解析失败，使用正则表达式提取: {value[:50]}...")
                        # 使用正则表达式提取 {{ variable }} 格式的变量
                        import re
                        pattern = r'\{\{\s*([^}]+?)\s*\}\}'
                        matches = re.findall(pattern, value)
                        for match in matches:
                            # 清理变量名，移除过滤器等
                            var_name = match.split('|')[0].split('.')[0].strip()
                            if var_name and not var_name.startswith('__'):
                                variables.add(var_name)
            elif isinstance(value, dict):
                self._extract_variables_from_dict(value, variables)
            elif isinstance(value, list):
                self._extract_variables_from_list(value, variables)

    def _extract_variables_from_list(self, data: List[Any], variables: set):
        """从列表中提取变量"""
        import re
        for item in data:
            if isinstance(item, str):
                if '{{' in item or '{%' in item or '{#' in item:
                    try:
                        # 使用Jinja2解析变量
                        ast = self.renderer.env.parse(item)
                        undeclared_vars = meta.find_undeclared_variables(ast)
                        variables.update(undeclared_vars)
                    except Exception as e:
                        # 如果解析失败，尝试使用正则表达式提取变量
                        logger.debug(f"列表项Jinja2解析失败，使用正则表达式提取: {item[:50]}...")
                        pattern = r'\{\{\s*([^}]+?)\s*\}\}'
                        matches = re.findall(pattern, item)
                        for match in matches:
                            var_name = match.split('|')[0].split('.')[0].strip()
                            if var_name and not var_name.startswith('__'):
                                variables.add(var_name)
            elif isinstance(item, dict):
                self._extract_variables_from_dict(item, variables)
            elif isinstance(item, list):
                self._extract_variables_from_list(item, variables)

    def _find_target_protocol(self, target_protocol_family: str, source_protocol_id: str) -> Optional[ProtocolTemplate]:
        """查找对应的目标协议模板"""
        # 简单的映射策略：假设A-1对应C-1，B-1对应C-1等
        # 实际应用中可能需要更复杂的映射逻辑
        source_number = source_protocol_id.split('-')[-1]
        target_protocol_id = f"{target_protocol_family}-{source_number}"

        return self.matcher.protocols.get(target_protocol_id)