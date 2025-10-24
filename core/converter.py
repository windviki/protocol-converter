"""
Core module for protocol conversion
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from jinja2 import Template, Environment, meta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProtocolTemplate:
    """协议模板数据类"""
    protocol_id: str
    protocol_family: str
    template_content: Dict[str, Any]
    variables: List[str]
    special_variables: List[str]


@dataclass
class ConversionResult:
    """转换结果数据类"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    matched_protocol: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


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
        
        return True


class VariableExtractor:
    """变量提取器"""
    
    def extract_variables(self, template: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从模板和数据中提取变量
        Args:
            template: 模板内容
            data: 输入数据
        Returns:
            变量键值对
        """
        variables = {}
        self._extract_from_dict(template, data, variables)
        return variables
    
    def _extract_from_dict(self, template: Dict[str, Any], data: Dict[str, Any], variables: Dict[str, Any]):
        """从字典中提取变量"""
        for key, template_value in template.items():
            if key in data:
                if isinstance(template_value, str):
                    # 检查是否是Jinja2变量
                    var_name = self._extract_variable_name(template_value)
                    if var_name:
                        variables[var_name] = data[key]
                elif isinstance(template_value, dict) and isinstance(data[key], dict):
                    self._extract_from_dict(template_value, data[key], variables)
                elif isinstance(template_value, list) and isinstance(data[key], list):
                    self._extract_from_list(template_value, data[key], variables)
    
    def _extract_from_list(self, template: List[Any], data: List[Any], variables: Dict[str, Any]):
        """从列表中提取变量"""
        if len(template) > 0 and len(data) > 0:
            if isinstance(template[0], dict) and isinstance(data[0], dict):
                self._extract_from_dict(template[0], data[0], variables)
    
    def _extract_variable_name(self, template_str: str) -> Optional[str]:
        """从模板字符串中提取变量名"""
        # 匹配 {{ variable_name }} 格式
        match = re.search(r'\{\{\s*([^}]+)\s*\}\}', template_str)
        if match:
            var_name = match.group(1).strip()
            # 过滤掉特殊变量（以__开头的）
            if not var_name.startswith('__'):
                return var_name
        return None


class TemplateRenderer:
    """模板渲染器"""
    
    def __init__(self, converter_functions: Dict[str, callable]):
        self.converter_functions = converter_functions
        self.env = Environment()
    
    def render(self, template: Dict[str, Any], variables: Dict[str, Any], 
               source_protocol: str, target_protocol: str, source_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染模板
        Args:
            template: 模板内容
            variables: 变量键值对
            source_protocol: 源协议
            target_protocol: 目标协议
            source_json: 源JSON数据
        Returns:
            渲染后的JSON数据
        """
        # 深拷贝模板以避免修改原始模板
        result = json.loads(json.dumps(template))
        self._render_dict(result, variables, source_protocol, target_protocol, source_json)
        return result
    
    def _render_dict(self, data: Dict[str, Any], variables: Dict[str, Any], 
                     source_protocol: str, target_protocol: str, source_json: Dict[str, Any]):
        """渲染字典"""
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = self._render_string(value, variables, source_protocol, target_protocol, source_json)
            elif isinstance(value, dict):
                self._render_dict(value, variables, source_protocol, target_protocol, source_json)
            elif isinstance(value, list):
                self._render_list(value, variables, source_protocol, target_protocol, source_json)
    
    def _render_list(self, data: List[Any], variables: Dict[str, Any], 
                     source_protocol: str, target_protocol: str, source_json: Dict[str, Any]):
        """渲染列表"""
        for i, item in enumerate(data):
            if isinstance(item, str):
                data[i] = self._render_string(item, variables, source_protocol, target_protocol, source_json)
            elif isinstance(item, dict):
                self._render_dict(item, variables, source_protocol, target_protocol, source_json)
            elif isinstance(item, list):
                self._render_list(item, variables, source_protocol, target_protocol, source_json)
    
    def _render_string(self, template_str: str, variables: Dict[str, Any], 
                       source_protocol: str, target_protocol: str, source_json: Dict[str, Any]) -> str:
        """渲染字符串"""
        # 检查是否是特殊变量（以__开头）
        special_var_match = re.search(r'\{\{\s*\__(\w+)\s*\}\}', template_str)
        if special_var_match:
            var_name = special_var_match.group(1)
            func_name = f"func_{var_name}"
            if func_name in self.converter_functions:
                # 调用转换函数
                result = self.converter_functions[func_name](source_protocol, target_protocol, source_json, variables)
                return re.sub(r'\{\{\s*\__\w+\s*\}\}', str(result), template_str)
        
        # 普通变量渲染
        try:
            jinja_template = self.env.from_string(template_str)
            return jinja_template.render(**variables)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return template_str


class ProtocolConverter:
    """协议转换器主类"""
    
    def __init__(self, converter_functions: Dict[str, callable] = None):
        self.matcher = ProtocolMatcher()
        self.extractor = VariableExtractor()
        self.converter_functions = converter_functions or {}
        self.renderer = TemplateRenderer(self.converter_functions)
    
    def load_protocol(self, protocol_id: str, protocol_family: str, template_content: Dict[str, Any]):
        """加载协议模板"""
        # 提取模板中的变量
        variables = self._extract_template_variables(template_content)
        special_variables = self._extract_special_variables(template_content)
        
        protocol = ProtocolTemplate(
            protocol_id=protocol_id,
            protocol_family=protocol_family,
            template_content=template_content,
            variables=variables,
            special_variables=special_variables
        )
        
        self.matcher.add_protocol(protocol)
        logger.info(f"Loaded protocol: {protocol_id}")
    
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
                source_json
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
                source_json
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
                # 使用Jinja2解析变量
                ast = self.renderer.env.parse(value)
                variables.update(meta.find_undeclared_variables(ast))
            elif isinstance(value, dict):
                self._extract_variables_from_dict(value, variables)
            elif isinstance(value, list):
                self._extract_variables_from_list(value, variables)
    
    def _extract_variables_from_list(self, data: List[Any], variables: set):
        """从列表中提取变量"""
        for item in data:
            if isinstance(item, str):
                ast = self.renderer.env.parse(item)
                variables.update(meta.find_undeclared_variables(item))
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