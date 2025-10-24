"""
Variable extraction module for extracting variables from templates and data
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set

from jinja2 import Environment, meta
from models.types import ArrayMarker

logger = logging.getLogger(__name__)


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
                    # 从data的相同键位置提取值
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