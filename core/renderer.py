"""
Template renderer module for rendering Jinja2 templates with context
"""

import json
import re
import logging
from typing import Dict, List, Any, Callable, Optional

from jinja2 import Environment, meta
from models.types import ConversionContext, ArrayMarker

logger = logging.getLogger(__name__)


class ConverterFunctionAdapter:
    """转换函数调用器，统一使用ConversionContext签名"""

    @staticmethod
    def call_converter_function(func: Callable, context: ConversionContext) -> Any:
        """
        调用转换函数，统一使用ConversionContext签名

        Args:
            func: 转换函数
            context: 转换上下文

        Returns:
            函数执行结果
        """
        try:
            # 统一使用新的ConversionContext签名
            return func(context)
        except TypeError as e:
            # 提供更好的错误信息
            raise ValueError(
                f"Converter function {func.__name__} must accept a single ConversionContext parameter. "
                f"Error: {e}. "
                f"Expected signature: func(context: ConversionContext) -> Any"
            )


class TemplateRenderer:
    """模板渲染器"""

    def __init__(self, converter_functions: Dict[str, callable]):
        self.converter_functions = converter_functions
        self.adapter = ConverterFunctionAdapter()
        # 配置Jinja2环境，添加常用的filters
        self.env = Environment()
        # 添加常用的内置filters
        self.env.filters['default'] = lambda x, default_value='': x if x is not None and x != '' else default_value
        self.env.filters['upper'] = lambda x: str(x).upper() if x else ''
        self.env.filters['lower'] = lambda x: str(x).lower() if x else ''
        self.env.filters['capitalize'] = lambda x: str(x).capitalize() if x else ''
        self.env.filters['length'] = lambda x: len(x) if hasattr(x, '__len__') else 0
        self.env.filters['sum'] = lambda x, attribute=None: sum(getattr(item, attribute, item) for item in x) if attribute else sum(x)

    def render(self, template: Dict[str, Any], variables: Dict[str, Any],
               source_protocol: str, target_protocol: str, source_json: Dict[str, Any],
               array_markers: List[ArrayMarker] = None,
               source_protocol_id: str = None, target_protocol_id: str = None,
               jinja_placeholders: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        渲染模板
        Args:
            template: 模板内容
            variables: 变量键值对
            source_protocol: 源协议
            target_protocol: 目标协议
            source_json: 源JSON数据
            array_markers: 数组标记列表
            source_protocol_id: 源协议ID
            target_protocol_id: 目标协议ID
            jinja_placeholders: Jinja2占位符映射
        Returns:
            渲染后的JSON数据
        """
        # 创建基础转换上下文
        context = ConversionContext(
            source_protocol=source_protocol,
            target_protocol=target_protocol,
            source_json=source_json,
            variables=variables,
            source_protocol_id=source_protocol_id,
            target_protocol_id=target_protocol_id
        )

        # 深拷贝模板以避免修改原始模板
        result = json.loads(json.dumps(template))

        # 如果有占位符映射，先恢复Jinja2语法
        if jinja_placeholders:
            result = self._restore_jinja_placeholders(result, jinja_placeholders)

        # 处理动态数组
        if array_markers:
            for marker in array_markers:
                if marker.is_dynamic:
                    self._render_dynamic_array(result, marker, context)

        # 常规渲染
        self._render_dict(result, context)
        return result

    def _render_dynamic_array(self, result: Dict[str, Any], marker: ArrayMarker, base_context: ConversionContext):
        """
        渲染动态数组

        Args:
            result: 渲染结果
            marker: 数组标记
            base_context: 基础转换上下文
        """
        # 获取数组数据
        array_data = self._get_nested_value(base_context.source_json, marker.field_path.split('.'))
        if not isinstance(array_data, list):
            # 如果指定路径没有数组数据，尝试从其他可能的路径获取
            array_data = self._find_array_data_heuristic(base_context.source_json)
            if not isinstance(array_data, list):
                return

        # 为每个数组元素生成渲染结果
        rendered_items = []
        array_total = len(array_data)

        for i, item_data in enumerate(array_data):
            # 创建该元素的变量集合
            item_variables = {}
            for var_name in base_context.variables:
                if var_name.endswith(f"_{i}"):
                    # 提取基础变量名（去掉索引）
                    base_var_name = var_name[:-len(f"_{i}")]
                    item_variables[base_var_name] = base_context.variables[var_name]

            # 如果没有找到索引变量，尝试直接从变量名匹配
            if not item_variables and isinstance(item_data, dict):
                # 从当前元素数据中提取变量
                item_variables = self._extract_variables_from_item_data(marker.template_item, item_data)

            # 创建当前元素的转换上下文
            element_context = ConversionContext(
                source_protocol=base_context.source_protocol,
                target_protocol=base_context.target_protocol,
                source_json=base_context.source_json,
                variables=item_variables,
                array_path=marker.field_path,
                array_index=i,
                array_total=array_total,
                current_element=item_data if isinstance(item_data, dict) else None,
                render_depth=base_context.render_depth + 1,
                parent_path=base_context.current_path,
                source_protocol_id=base_context.source_protocol_id,
                target_protocol_id=base_context.target_protocol_id,
                protocol_family=base_context.protocol_family,
                processed_items=i
            )

            # 渲染该元素
            rendered_item = json.loads(json.dumps(marker.template_item))
            self._render_dict(rendered_item, element_context)
            rendered_items.append(rendered_item)

        # 将结果设置回输出
        self._set_nested_value(result, marker.field_path.split('.'), rendered_items)

    def _find_array_data_heuristic(self, source_json: Dict[str, Any]) -> Optional[List[Any]]:
        """使用启发式方法查找数组数据"""
        # 查找所有列表类型的字段
        for key, value in source_json.items():
            if isinstance(value, list) and len(value) > 0:
                # 跳过只包含字符串标记的数组（如动态数组标记）
                if not (len(value) == 1 and isinstance(value[0], str) and value[0].startswith("{#")):
                    return value
        return None

    def _extract_variables_from_item_data(self, template_item: Dict[str, Any], item_data: Dict[str, Any]) -> Dict[str, Any]:
        """从模板项和元素数据中提取变量"""
        variables = {}
        self._extract_variables_from_dict(template_item, set())

        # 从模板中提取变量名，然后从item_data中获取对应的值
        template_vars = set()
        self._collect_template_variables(template_item, template_vars)

        for var_name in template_vars:
            if var_name in item_data:
                variables[var_name] = item_data[var_name]

        return variables

    def _collect_template_variables(self, template: Any, variables: set):
        """收集模板中的所有变量名"""
        if isinstance(template, str):
            try:
                ast = self.env.parse(template)
                variables.update(meta.find_undeclared_variables(ast))
            except:
                pass
        elif isinstance(template, dict):
            for value in template.values():
                self._collect_template_variables(value, variables)
        elif isinstance(template, list):
            for item in template:
                self._collect_template_variables(item, variables)

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

    def _render_dict(self, data: Dict[str, Any], context: ConversionContext):
        """渲染字典"""
        for key, value in data.items():
            if isinstance(value, str):
                # 设置当前路径
                old_path = context.current_path
                context.current_path = f"{old_path}.{key}" if old_path else key

                data[key] = self._render_string(value, context)
                context.current_path = old_path
            elif isinstance(value, dict):
                old_path = context.current_path
                context.current_path = f"{old_path}.{key}" if old_path else key
                context.render_depth += 1
                self._render_dict(value, context)
                context.render_depth -= 1
                context.current_path = old_path
            elif isinstance(value, list):
                old_path = context.current_path
                context.current_path = f"{old_path}.{key}" if old_path else key
                self._render_list(value, context)

    def _render_list(self, data: List[Any], context: ConversionContext):
        """渲染列表"""
        for i, item in enumerate(data):
            if isinstance(item, str):
                data[i] = self._render_string(item, context)
            elif isinstance(item, dict):
                context.render_depth += 1
                self._render_dict(item, context)
                context.render_depth -= 1
            elif isinstance(item, list):
                context.render_depth += 1
                self._render_list(item, context)
                context.render_depth -= 1

    def _render_string(self, template_str: str, context: ConversionContext) -> str:
        """渲染字符串"""
        # 预处理模板字符串，修复Jinja2语法兼容性问题
        template_str = self._preprocess_template(template_str)

        # 检查是否是特殊变量（以__开头）
        special_var_match = re.search(r'\{\{\s*\__(\w+)\s*\}\}', template_str)
        if special_var_match:
            var_name = special_var_match.group(1)
            func_name = f"func_{var_name}"
            if func_name in self.converter_functions:
                # 使用适配器调用转换函数
                result = self.adapter.call_converter_function(
                    self.converter_functions[func_name],
                    context
                )
                return re.sub(r'\{\{\s*\__\w+\s*\}\}', str(result), template_str)

        # 普通变量渲染
        try:
            jinja_template = self.env.from_string(template_str)
            return jinja_template.render(**context.variables)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            logger.error(f"Template string: {template_str}")
            logger.error(f"Available variables: {list(context.variables.keys())}")
            # 尝试提供一个部分渲染的结果或者有意义的默认值
            return self._fallback_render(template_str, context)

    def _extract_variables_from_dict(self, data: Dict[str, Any], variables: set):
        """从字典中提取变量"""
        for value in data.values():
            if isinstance(value, str):
                # 使用Jinja2解析变量
                ast = self.env.parse(value)
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
                    ast = self.env.parse(item)
                    variables.update(meta.find_undeclared_variables(ast))
                except Exception:
                    # 如果解析失败，跳过该项
                    pass
            elif isinstance(item, dict):
                self._extract_variables_from_dict(item, variables)
            elif isinstance(item, list):
                self._extract_variables_from_list(item, variables)

    def _fallback_render(self, template_str: str, context: ConversionContext) -> str:
        """回退渲染方法，处理模板渲染失败的情况"""
        import re

        result = template_str

        # 首先处理函数调用
        def replace_func_call(match):
            func_name = match.group(1).strip()
            try:
                from converters.functions import get_converter_function
                func = get_converter_function(func_name)
                if func:
                    return func(context)
                return f"[FUNC_ERROR:{func_name}]"
            except Exception as e:
                logger.error(f"Function call error {func_name}: {e}")
                return f"[FUNC_ERROR:{func_name}]"

        # 替换函数调用 {{ func_name() }}
        result = re.sub(r'\{\{\s*(\w+)\(\)\s*\}\}', replace_func_call, result)

        # 替换简单的变量
        def replace_simple_var(match):
            var_name = match.group(1).strip()
            if var_name in context.variables:
                return str(context.variables[var_name])
            return f"[MISSING:{var_name}]"

        result = re.sub(r'\{\{\s*([^}|]+?)\s*\}\}', replace_simple_var, result)

        # 处理带过滤器的变量 - 包括默认值过滤器
        def replace_filtered_var(match):
            var_expr = match.group(1).strip()

            # 处理默认值过滤器，如: city | default '上海'
            if 'default' in var_expr:
                import re
                # 匹配 default 'value' 或 default "value"
                default_match = re.search(r"default\s+['\"]([^'\"]*)['\"]", var_expr)
                var_name = var_expr.split('|')[0].strip()

                if var_name in context.variables and context.variables[var_name] is not None:
                    return str(context.variables[var_name])
                elif default_match:
                    return default_match.group(1)
                else:
                    return f"[MISSING:{var_name}]"

            # 处理其他过滤器
            var_name = var_expr.split('|')[0].strip()
            if var_name in context.variables:
                value = context.variables[var_name]
                # 处理一些常用过滤器
                if '| upper' in var_expr:
                    return str(value).upper()
                elif '| lower' in var_expr:
                    return str(value).lower()
                else:
                    return str(value)
            return f"[MISSING:{var_name}]"

        result = re.sub(r'\{\{\s*([^}]+?)\s*\}\}', replace_filtered_var, result)

        return result

    def _preprocess_template(self, template_str: str) -> str:
        """
        预处理模板字符串，修复Jinja2语法兼容性问题

        Args:
            template_str: 原始模板字符串

        Returns:
            str: 处理后的模板字符串
        """
        import re

        # 添加调试信息
        original_str = template_str

        # 将 default 'value' 或 default "value" 替换为 default('value')
        def replace_default_syntax(match):
            var_expr = match.group(0)
            # 将 default 'value' 或 default "value" 替换为 default('value')
            result = re.sub(r"default\s+['\"]([^'\"]*)['\"]", r'default("\1")', var_expr)
            return result

        # 使用正则表达式替换所有default过滤器语法
        template_str = re.sub(r"\{\{\s*([^}]+default\s+['\"][^'\"]*['\"][^}]*)\}\}", replace_default_syntax, template_str)

        # 如果字符串有变化，记录调试信息
        if template_str != original_str:
            logger.debug(f"Preprocessed template: {original_str} -> {template_str}")

        return template_str

    def _restore_jinja_placeholders(self, data: Any, jinja_placeholders: Dict[str, Any]) -> Any:
        """
        递归恢复Jinja2占位符为原始语法

        Args:
            data: 包含占位符的数据结构
            jinja_placeholders: 占位符映射字典

        Returns:
            恢复了Jinja2语法的数据结构
        """
        if isinstance(data, dict):
            restored = {}
            for key, value in data.items():
                restored[key] = self._restore_jinja_placeholders(value, jinja_placeholders)
            return restored

        elif isinstance(data, list):
            restored = []
            for item in data:
                restored.append(self._restore_jinja_placeholders(item, jinja_placeholders))
            return restored

        elif isinstance(data, str):
            # 检查是否是占位符
            if data in jinja_placeholders:
                placeholder_info = jinja_placeholders[data]
                return placeholder_info.original_content
            else:
                return data
        else:
            return data