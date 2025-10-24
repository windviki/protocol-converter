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
class ArrayMarker:
    """数组处理标记"""
    field_path: str  # 字段路径，如 "items"
    is_dynamic: bool  # 是否动态处理整个数组
    template_item: Dict[str, Any]  # 数组项的模板结构


@dataclass
class ProtocolTemplate:
    """协议模板数据类"""
    protocol_id: str
    protocol_family: str
    template_content: Dict[str, Any]
    variables: List[str]
    special_variables: List[str]
    array_markers: List[ArrayMarker]  # 数组处理标记列表


@dataclass
class ConversionResult:
    """转换结果数据类"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    matched_protocol: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ArrayMarkerParser:
    """数组标记解析器"""

    @staticmethod
    def parse_array_markers(template: Dict[str, Any], path: str = "") -> List[ArrayMarker]:
        """
        解析模板中的数组处理标记

        Args:
            template: 模板内容
            path: 当前字段路径

        Returns:
            发现的数组标记列表
        """
        markers = []

        for key, value in template.items():
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, list) and len(value) > 0:
                # 检查是否包含动态数组标记
                first_item = value[0]
                second_item = value[1] if len(value) > 1 else None

                if (isinstance(first_item, str) and "# array_dynamic: true" in first_item and
                    isinstance(second_item, dict)):
                    # 找到动态数组标记
                    marker = ArrayMarker(
                        field_path=current_path,
                        is_dynamic=True,
                        template_item=second_item
                    )

                    markers.append(marker)

                elif isinstance(first_item, dict):
                    # 递归检查嵌套结构
                    markers.extend(ArrayMarkerParser.parse_array_markers(first_item, current_path))

            elif isinstance(value, dict):
                # 递归检查嵌套结构
                markers.extend(ArrayMarkerParser.parse_array_markers(value, current_path))

        return markers


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


class VariableExtractor:
    """变量提取器"""

    def __init__(self):
        # 配置Jinja2环境用于解析变量
        self.env = Environment()

    def extract_variables(self, template: Dict[str, Any], data: Dict[str, Any],
                         array_markers: List[ArrayMarker] = None) -> Dict[str, Any]:
        """
        从模板和数据中提取变量
        Args:
            template: 模板内容
            data: 输入数据
            array_markers: 数组标记列表
        Returns:
            变量键值对
        """
        variables = {}
        self._extract_from_dict(template, data, variables)

        # 处理动态数组
        if array_markers:
            for marker in array_markers:
                if marker.is_dynamic:
                    self._extract_dynamic_array_variables(marker, data, variables)

        return variables

    def _extract_dynamic_array_variables(self, marker: ArrayMarker, data: Dict[str, Any], variables: Dict[str, Any]):
        """
        从动态数组中提取所有元素的变量

        Args:
            marker: 数组标记
            data: 输入数据
            variables: 变量字典
        """
        # 获取数组数据
        array_data = self._get_nested_value(data, marker.field_path.split('.'))
        if not isinstance(array_data, list):
            return

        # 从模板项中提取变量名
        template_vars = self._extract_template_variables(marker.template_item)

        # 为每个数组元素提取变量
        for i, item_data in enumerate(array_data):
            if isinstance(item_data, dict):
                for var_name in template_vars:
                    if var_name in item_data:
                        # 为每个元素添加索引变量
                        indexed_var_name = f"{var_name}_{i}"
                        variables[indexed_var_name] = item_data[var_name]

    def _get_nested_value(self, data: Dict[str, Any], path_parts: List[str]) -> Any:
        """获取嵌套字典中的值"""
        current = data
        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _extract_template_variables(self, template: Dict[str, Any]) -> List[str]:
        """从模板中提取变量名"""
        # 创建一个临时的variables字典来收集变量
        temp_variables = {}
        self._extract_from_dict(template, {}, temp_variables)

        # 将字典的键转换为set
        variables = set(temp_variables.keys())
        return [v for v in variables if not v.startswith('__')]
    
    def _extract_from_dict(self, template: Dict[str, Any], data: Dict[str, Any], variables: Dict[str, Any]):
        """从字典中提取变量"""
        for key, template_value in template.items():
            if isinstance(template_value, str):
                # 检查是否是Jinja2变量
                var_name = self._extract_variable_name(template_value)
                if var_name:
                    # 从数据的相同键位置提取值
                    if key in data:
                        variables[var_name] = data[key]
                    else:
                        # 如果对应键不存在，设为None
                        variables[var_name] = None
            elif isinstance(template_value, dict):
                # 递归提取嵌套字典中的变量
                self._extract_from_dict(template_value, data.get(key, {}), variables)
            elif isinstance(template_value, list) and isinstance(data.get(key, []), list):
                self._extract_from_list(template_value, data.get(key, []), variables)
    
    def _extract_from_list(self, template: List[Any], data: List[Any], variables: Dict[str, Any]):
        """从列表中提取变量"""
        if len(template) > 0 and len(data) > 0:
            if isinstance(template[0], dict) and isinstance(data[0], dict):
                self._extract_from_dict(template[0], data[0], variables)

    def _find_value_in_data(self, var_name: str, data: Dict[str, Any]) -> Any:
        """在数据结构中查找变量值"""
        # 如果是直接的键
        if var_name in data:
            return data[var_name]

        # 在嵌套结构中查找
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    result = self._find_value_in_data(var_name, value)
                    if result is not None:
                        return result
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            result = self._find_value_in_data(var_name, item)
                            if result is not None:
                                return result

        # 如果找不到，返回变量名本身（这可能是测试失败的原因）
        # 但更好的做法是返回None，让调用者处理
        return None
    
    def _extract_variable_name(self, template_str: str) -> Optional[str]:
        """从模板字符串中提取变量名"""
        # 使用Jinja2解析来提取变量
        try:
            ast = self.env.parse(template_str)
            variables = meta.find_undeclared_variables(ast)
            # 过滤掉特殊变量（以__开头的）
            normal_vars = [var for var in variables if not var.startswith('__')]
            return normal_vars[0] if normal_vars else None
        except Exception:
            # 如果解析失败，回退到正则表达式方法
            match = re.search(r'\{\{\s*([^}|]+)\s*(?:\|[^}]+)?\}\}', template_str)
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
        # 配置Jinja2环境，添加常用的filters
        self.env = Environment()
        # 添加常用的内置filters
        self.env.filters['upper'] = lambda x: str(x).upper() if x else ''
        self.env.filters['lower'] = lambda x: str(x).lower() if x else ''
        self.env.filters['capitalize'] = lambda x: str(x).capitalize() if x else ''
        self.env.filters['length'] = lambda x: len(x) if hasattr(x, '__len__') else 0
        self.env.filters['sum'] = lambda x, attribute=None: sum(getattr(item, attribute, item) for item in x) if attribute else sum(x)
    
    def render(self, template: Dict[str, Any], variables: Dict[str, Any],
               source_protocol: str, target_protocol: str, source_json: Dict[str, Any],
               array_markers: List[ArrayMarker] = None) -> Dict[str, Any]:
        """
        渲染模板
        Args:
            template: 模板内容
            variables: 变量键值对
            source_protocol: 源协议
            target_protocol: 目标协议
            source_json: 源JSON数据
            array_markers: 数组标记列表
        Returns:
            渲染后的JSON数据
        """
        # 深拷贝模板以避免修改原始模板
        result = json.loads(json.dumps(template))

        # 处理动态数组
        if array_markers:
            for marker in array_markers:
                if marker.is_dynamic:
                    self._render_dynamic_array(result, marker, variables, source_protocol, target_protocol, source_json)

        # 常规渲染
        self._render_dict(result, variables, source_protocol, target_protocol, source_json)
        return result

    def _render_dynamic_array(self, result: Dict[str, Any], marker: ArrayMarker,
                             variables: Dict[str, Any], source_protocol: str,
                             target_protocol: str, source_json: Dict[str, Any]):
        """
        渲染动态数组

        Args:
            result: 渲染结果
            marker: 数组标记
            variables: 变量键值对
            source_protocol: 源协议
            target_protocol: 目标协议
            source_json: 源JSON数据
        """
        # 获取数组数据
        array_data = self._get_nested_value(source_json, marker.field_path.split('.'))
        if not isinstance(array_data, list):
            return

        # 为每个数组元素生成渲染结果
        rendered_items = []
        for i, item_data in enumerate(array_data):
            # 创建该元素的变量集合
            item_variables = {}
            for var_name in variables:
                if var_name.endswith(f"_{i}"):
                    # 提取基础变量名（去掉索引）
                    base_var_name = var_name[:-len(f"_{i}")]
                    item_variables[base_var_name] = variables[var_name]

            # 渲染该元素
            rendered_item = json.loads(json.dumps(marker.template_item))
            self._render_dict(rendered_item, item_variables, source_protocol, target_protocol, source_json)
            rendered_items.append(rendered_item)

        # 将结果设置回输出
        self._set_nested_value(result, marker.field_path.split('.'), rendered_items)

    def _set_nested_value(self, data: Dict[str, Any], path_parts: List[str], value: Any):
        """在嵌套字典中设置值"""
        current = data
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path_parts[-1]] = value

    def _get_nested_value(self, data: Dict[str, Any], path_parts: List[str]) -> Any:
        """获取嵌套字典中的值"""
        current = data
        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
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
        logger.info(f"Loaded protocol: {protocol_id} with {len(array_markers)} array markers")
    
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
                target_protocol_template.array_markers
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
                try:
                    ast = self.renderer.env.parse(item)
                    variables.update(meta.find_undeclared_variables(ast))
                except Exception:
                    # 如果解析失败，跳过该项
                    pass
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