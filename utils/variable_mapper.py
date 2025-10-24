"""
变量路径映射器
提供Jinja2变量到YAML路径的映射功能
"""

from typing import Dict, List, Set, Any, Optional, Tuple
import re
from dataclasses import dataclass
import logging

from .yaml_path import YamlPath, PathError
from .yaml_processor import YamlProcessor, Jinja2Placeholder
from core.field_mapper import create_field_mapper

logger = logging.getLogger(__name__)

@dataclass
class VariableInfo:
    """变量信息"""
    name: str
    yaml_paths: List[str]  # 可能的多个路径
    variable_type: str  # 'regular', 'special', or 'mapping'
    filters: List[str]  # 使用的过滤器
    default_value: Optional[str] = None
    context_required: bool = False  # 是否需要转换上下文
    jinja_expression: str = ""  # 原始Jinja2表达式
    is_mapping: bool = False  # 是否需要field mapping

@dataclass
class VariableMappingResult:
    """变量映射结果"""
    variable_map: Dict[str, VariableInfo]
    regular_variables: Set[str]
    special_variables: Set[str]
    mapping_variables: Set[str] = None  # 需要field mapping的变量
    path_statistics: Dict[str, int] = None  # 路径使用统计
    mapping_report: str = ""

class VariableMapper:
    """变量路径映射器"""

    def __init__(self):
        self.yaml_processor = YamlProcessor()
        self.field_mapper = create_field_mapper()

        # Jinja2模式
        self.variable_pattern = re.compile(r'\{\{\s*([^}]+)\s*\}\}')
        self.mapping_variable_pattern = re.compile(r'\$\{\{\s*([^}]+)\s*\}\}')
        self.filter_pattern = re.compile(r'([^|]+(?:\([^)]*\))?)\s*\|\s*([^}]+)')
        self.function_pattern = re.compile(r'(\w+)\s*\(')
        self.array_marker_pattern = re.compile(r'\{\#\s*array_dynamic:\s*true\s*\#\}')

    def map_variables(self, yaml_template: Any,
                     jinja_placeholders: Dict[str, Jinja2Placeholder]) -> VariableMappingResult:
        """
        映射所有Jinja2变量到YAML路径

        Args:
            yaml_template: YAML模板数据
            jinja_placeholders: Jinja2占位符映射

        Returns:
            变量映射结果
        """
        variable_map = {}
        path_statistics = {}
        array_markers = set()

        # 首先识别动态数组标记
        self._identify_array_markers(yaml_template, array_markers)

        # 递归遍历YAML结构
        self._traverse_and_map(
            yaml_template, "", variable_map, jinja_placeholders,
            path_statistics, array_markers
        )

        # 分类变量
        regular_variables = {name for name, info in variable_map.items()
                           if info.variable_type == 'regular'}
        special_variables = {name for name, info in variable_map.items()
                           if info.variable_type == 'special'}
        mapping_variables = {name for name, info in variable_map.items()
                           if info.variable_type == 'mapping'}

        # 生成映射报告
        mapping_report = self._generate_mapping_report(
            variable_map, regular_variables, special_variables, mapping_variables,
            path_statistics, array_markers
        )

        logger.info(f"Mapped {len(variable_map)} variables to {len(path_statistics)} paths")
        logger.info(f"Regular: {len(regular_variables)}, Special: {len(special_variables)}, Mapping: {len(mapping_variables)}")

        return VariableMappingResult(
            variable_map=variable_map,
            regular_variables=regular_variables,
            special_variables=special_variables,
            mapping_variables=mapping_variables,
            path_statistics=path_statistics,
            mapping_report=mapping_report
        )

    def _identify_array_markers(self, node: Any, array_markers: Set[str]) -> None:
        """识别动态数组标记"""
        if isinstance(node, str):
            if self.array_marker_pattern.search(node):
                array_markers.add(node)
        elif isinstance(node, dict):
            for value in node.values():
                self._identify_array_markers(value, array_markers)
        elif isinstance(node, list):
            for item in node:
                self._identify_array_markers(item, array_markers)

    def _traverse_and_map(self, node: Any, current_path: str,
                         variable_map: Dict[str, VariableInfo],
                         jinja_placeholders: Dict[str, Jinja2Placeholder],
                         path_statistics: Dict[str, int],
                         array_markers: Set[str]) -> None:
        """递归遍历并映射变量"""

        if isinstance(node, dict):
            for key, value in node.items():
                new_path = f"{current_path}.{key}" if current_path else key
                self._process_node(
                    value, new_path, variable_map, jinja_placeholders,
                    path_statistics, array_markers
                )

        elif isinstance(node, list):
            for i, item in enumerate(node):
                new_path = f"{current_path}[{i}]" if current_path else f"[{i}]"
                self._process_node(
                    item, new_path, variable_map, jinja_placeholders,
                    path_statistics, array_markers
                )

    def _process_node(self, node: Any, current_path: str,
                     variable_map: Dict[str, VariableInfo],
                     jinja_placeholders: Dict[str, Jinja2Placeholder],
                     path_statistics: Dict[str, int],
                     array_markers: Set[str]) -> None:
        """处理单个节点"""

        # 检查是否为动态数组标记
        if isinstance(node, str) and node in array_markers:
            # 动态数组的子项需要特殊处理
            return

        # 检查是否为Jinja2占位符
        if isinstance(node, str):
            # 查找对应的占位符
            placeholder_info = self._find_placeholder_info(node, jinja_placeholders)
            if placeholder_info:
                # 获取原始内容
                original_content = placeholder_info.original_content
                # 检查占位符类型
                if placeholder_info.type == 'mapping':
                    # 这是mapping变量占位符
                    expr = original_content[3:-2]  # 去掉 ${{ 和 }}
                    var_info = VariableInfo(
                        name=expr.strip(),
                        yaml_paths=[current_path],
                        variable_type='mapping',
                        filters=[],
                        is_mapping=True,
                        jinja_expression=original_content
                    )
                    self._add_variable_mapping(
                        var_info, current_path, variable_map, path_statistics
                    )
                else:
                    # 普通变量占位符
                    variable_infos = self._parse_variable_expression(original_content)
                    for var_info in variable_infos:
                        self._add_variable_mapping(
                            var_info, current_path, variable_map, path_statistics
                        )
            else:
                # 检查字符串中是否包含mapping变量表达式 ${{...}}
                mapping_expressions = self.mapping_variable_pattern.findall(node)
                for expr in mapping_expressions:
                    var_info = VariableInfo(
                        name=expr.strip(),
                        yaml_paths=[current_path],
                        variable_type='mapping',
                        filters=[],
                        is_mapping=True,
                        jinja_expression="${{{" + expr.strip() + "}}}"
                    )
                    self._add_variable_mapping(
                        var_info, current_path, variable_map, path_statistics
                    )

                # 检查字符串中是否包含普通Jinja2表达式 {{...}}
                expressions = self.variable_pattern.findall(node)
                for expr in expressions:
                    variable_infos = self._parse_variable_expression(expr)
                    for var_info in variable_infos:
                        self._add_variable_mapping(
                            var_info, current_path, variable_map, path_statistics
                        )

        # 递归处理嵌套结构
        elif isinstance(node, (dict, list)):
            self._traverse_and_map(
                node, current_path, variable_map, jinja_placeholders,
                path_statistics, array_markers
            )

    def _find_placeholder_info(self, text: str,
                             jinja_placeholders: Dict[str, Jinja2Placeholder]) -> Optional[Jinja2Placeholder]:
        """找到文本对应的占位符信息"""
        for placeholder_info in jinja_placeholders.values():
            # 直接匹配
            if text == placeholder_info.placeholder:
                return placeholder_info
            # 处理带$前缀的情况
            if text == '$' + placeholder_info.placeholder:
                return placeholder_info
        return None

    def _parse_variable_expression(self, expression: str) -> List[VariableInfo]:
        """解析Jinja2变量表达式"""
        variable_infos = []

        # 清理表达式
        expr = expression.strip()

        # 移除Jinja2变量标记 {{ 和 }}
        if expr.startswith('{{') and expr.endswith('}}'):
            expr = expr[2:-2].strip()

        # 处理复杂表达式（包含函数调用、过滤等）
        if '|' in expr:
            # 有过滤器的情况
            filter_match = self.filter_pattern.search(expr)
            if filter_match:
                var_part = filter_match.group(1).strip()
                filter_part = filter_match.group(2).strip()

                # 解析变量部分
                var_names = self._extract_variable_names_from_complex(var_part)
                filters = self._parse_filters(filter_part)

                for var_name in var_names:
                    var_info = VariableInfo(
                        name=var_name,
                        yaml_paths=[],  # 稍后填充
                        variable_type='special' if var_name.startswith('__') else 'regular',
                        filters=filters,
                        context_required=var_name.startswith('__'),
                        jinja_expression=expression
                    )
                    variable_infos.append(var_info)

        else:
            # 简单变量或函数调用
            var_names = self._extract_variable_names_from_complex(expr)

            for var_name in var_names:
                var_info = VariableInfo(
                    name=var_name,
                    yaml_paths=[],  # 稍后填充
                    variable_type='special' if var_name.startswith('__') else 'regular',
                    filters=[],
                    context_required=var_name.startswith('__'),
                    jinja_expression=expression
                )
                variable_infos.append(var_info)

        return variable_infos

    def _extract_variable_names_from_complex(self, expr: str) -> List[str]:
        """从复杂表达式中提取变量名"""
        var_names = []

        # 检查是否是函数调用
        func_match = self.function_pattern.search(expr)
        if func_match:
            # 函数调用，不包含变量
            return []

        # 处理字典访问
        if '.' in expr:
            # 可能有嵌套访问，如 user.name
            parts = expr.split('.')
            if parts:
                var_names.append(parts[0].strip())
        else:
            # 简单变量
            var_names.append(expr.strip())

        return [name for name in var_names if name]

    def _parse_filters(self, filter_str: str) -> List[str]:
        """解析过滤器字符串"""
        filters = []

        # 清理过滤器字符串
        filter_str = filter_str.strip()

        # 处理多个过滤器（用 | 分隔）
        filter_parts = [f.strip() for f in filter_str.split('|') if f.strip()]

        for filter_part in filter_parts:
            # 处理带参数的过滤器，如 default('unknown')
            if '(' in filter_part and filter_part.endswith(')'):
                filter_name = filter_part.split('(')[0].strip()
                filters.append(filter_name)
            else:
                filters.append(filter_part)

        return filters

    def _add_variable_mapping(self, var_info: VariableInfo,
                            yaml_path: str,
                            variable_map: Dict[str, VariableInfo],
                            path_statistics: Dict[str, int]) -> None:
        """添加变量映射"""
        if var_info.name in variable_map:
            # 变量已存在，添加新路径
            existing = variable_map[var_info.name]
            if yaml_path not in existing.yaml_paths:
                existing.yaml_paths.append(yaml_path)

                # 合并过滤器
                for filter_name in var_info.filters:
                    if filter_name not in existing.filters:
                        existing.filters.append(filter_name)

                # 更新默认值
                if var_info.default_value and not existing.default_value:
                    existing.default_value = var_info.default_value
        else:
            # 新变量
            var_info.yaml_paths = [yaml_path]
            variable_map[var_info.name] = var_info

        # 更新路径统计
        if yaml_path not in path_statistics:
            path_statistics[yaml_path] = 0
        path_statistics[yaml_path] += 1

    def _generate_mapping_report(self, variable_map: Dict[str, VariableInfo],
                               regular_variables: Set[str],
                               special_variables: Set[str],
                               mapping_variables: Set[str] = None,
                               path_statistics: Dict[str, int] = None,
                               array_markers: Set[str] = None) -> str:
        """生成变量映射报告"""
        lines = []
        lines.append("Variable Path Mapping Report")
        lines.append("=" * 40)

        # 总体统计
        lines.append(f"Total Variables: {len(variable_map)}")
        lines.append(f"Regular Variables: {len(regular_variables)}")
        lines.append(f"Special Variables: {len(special_variables)}")
        lines.append(f"Unique Paths: {len(path_statistics)}")
        lines.append(f"Array Markers: {len(array_markers)}")

        # 普通变量详情
        if regular_variables:
            lines.append(f"\nRegular Variables ({len(regular_variables)}):")
            lines.append("-" * 25)
            for var_name in sorted(regular_variables):
                var_info = variable_map[var_name]
                lines.append(f"  {var_name}:")
                for path in var_info.yaml_paths:
                    usage_count = path_statistics.get(path, 0)
                    lines.append(f"    - {path} (used {usage_count} times)")
                if var_info.filters:
                    lines.append(f"    filters: {', '.join(var_info.filters)}")
                if var_info.default_value:
                    lines.append(f"    default: {var_info.default_value}")

        # 特殊变量详情
        if special_variables:
            lines.append(f"\nSpecial Variables ({len(special_variables)}):")
            lines.append("-" * 25)
            for var_name in sorted(special_variables):
                var_info = variable_map[var_name]
                lines.append(f"  {var_name}:")
                for path in var_info.yaml_paths:
                    usage_count = path_statistics.get(path, 0)
                    lines.append(f"    - {path} (used {usage_count} times)")
                lines.append(f"    context_required: {var_info.context_required}")

        # 路径使用统计
        if path_statistics:
            lines.append(f"\nPath Usage Statistics:")
            lines.append("-" * 25)
            sorted_paths = sorted(path_statistics.items(), key=lambda x: x[1], reverse=True)
            for path, count in sorted_paths[:10]:  # 显示前10个最常用的路径
                lines.append(f"  {path}: {count} times")

        # 数组标记
        if array_markers:
            lines.append(f"\nDynamic Array Markers:")
            lines.append("-" * 25)
            for marker in array_markers:
                lines.append(f"  {marker}")

        return "\n".join(lines)

    def process_mapping_variables(self, mapping_vars: Dict[str, Any],
                                source_protocol: str, target_protocol: str,
                                source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用field mapper处理mapping变量

        Args:
            mapping_vars: 需要映射的变量字典
            source_protocol: 源协议ID
            target_protocol: 目标协议ID
            source_data: 源数据

        Returns:
            映射后的变量字典
        """
        if not mapping_vars:
            return {}

        return self.field_mapper.process_mapping(
            mapping_vars, source_protocol, target_protocol, source_data
        )

    def extract_variables_from_template(self, template_content: str) -> Tuple[Set[str], Set[str]]:
        """
        从模板内容中提取变量（不进行路径映射）

        Args:
            template_content: 模板内容字符串

        Returns:
            (regular_variables, special_variables)
        """
        regular_vars = set()
        special_vars = set()

        # 查找所有变量表达式
        expressions = self.variable_pattern.findall(template_content)

        for expr in expressions:
            var_names = self._extract_variable_names_from_complex(expr.strip())
            for var_name in var_names:
                if var_name.startswith('__'):
                    special_vars.add(var_name)
                else:
                    regular_vars.add(var_name)

        return regular_vars, special_vars

    def validate_variable_mapping(self, variable_map: Dict[str, VariableInfo],
                                available_paths: List[str]) -> List[str]:
        """
        验证变量映射的有效性

        Args:
            variable_map: 变量映射
            available_paths: 可用的路径列表

        Returns:
            验证警告列表
        """
        warnings = []

        for var_name, var_info in variable_map.items():
            # 检查路径是否存在
            for path in var_info.yaml_paths:
                if path not in available_paths:
                    warnings.append(f"Variable '{var_name}' references unknown path: {path}")

            # 检查特殊变量是否需要上下文
            if var_info.variable_type == 'special' and not var_info.context_required:
                warnings.append(f"Special variable '{var_name}' might require context")

            # 检查过滤器是否已知
            known_filters = {'upper', 'lower', 'capitalize', 'default', 'title'}
            for filter_name in var_info.filters:
                if filter_name not in known_filters:
                    warnings.append(f"Unknown filter '{filter_name}' used by variable '{var_name}'")

        return warnings

    def get_variables_by_filter(self, variable_map: Dict[str, VariableInfo],
                              filter_name: str) -> List[str]:
        """
        获取使用特定过滤器的变量列表

        Args:
            variable_map: 变量映射
            filter_name: 过滤器名称

        Returns:
            变量名列表
        """
        return [name for name, info in variable_map.items()
                if filter_name in info.filters]

    def get_variables_by_path(self, variable_map: Dict[str, VariableInfo],
                            path_pattern: str) -> List[str]:
        """
        获取使用特定路径模式的变量列表

        Args:
            variable_map: 变量映射
            path_pattern: 路径模式（支持简单通配符）

        Returns:
            变量名列表
        """
        pattern = path_pattern.replace('*', '.*')
        regex = re.compile(pattern)

        matching_vars = []
        for name, info in variable_map.items():
            for path in info.yaml_paths:
                if regex.search(path):
                    matching_vars.append(name)
                    break

        return matching_vars

# 便利函数
def map_template_variables(yaml_template: Any,
                         jinja_placeholders: Dict[str, Jinja2Placeholder]) -> VariableMappingResult:
    """映射模板变量的便利函数"""
    mapper = VariableMapper()
    return mapper.map_variables(yaml_template, jinja_placeholders)

def extract_template_variables(template_content: str) -> Tuple[Set[str], Set[str]]:
    """提取模板变量的便利函数"""
    mapper = VariableMapper()
    return mapper.extract_variables_from_template(template_content)