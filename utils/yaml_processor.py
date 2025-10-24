"""
YAML处理工具模块
提供Jinja2语法保护、JSON-YAML转换、YAML schema生成等功能
"""

import re
import json
import yaml
from typing import Any, Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Jinja2Placeholder:
    """Jinja2占位符信息"""
    id: str
    original_content: str
    placeholder: str
    type: str  # 'variable', 'statement', 'comment'
    location: Optional[str] = None

class YamlProcessor:
    """YAML处理器"""

    def __init__(self):
        # Jinja2语法模式
        self.variable_pattern = re.compile(r'\{\{\s*([^{}]+?)\s*\}\}')
        self.statement_pattern = re.compile(r'\{\%\s*([^%]*?)\s*\%\}')
        self.comment_pattern = re.compile(r'\{\#\s*([^#]*?)\s*\#\}')

        # 占位符映射
        self.placeholder_map: Dict[str, Jinja2Placeholder] = {}
        self.placeholder_counter = 0

    def protect_jinja_syntax(self, data: Any, context_path: str = "") -> Tuple[Any, Dict[str, Jinja2Placeholder]]:
        """
        保护Jinja2语法，替换为占位符

        Args:
            data: 要处理的数据（字典、列表或字符串）
            context_path: 当前上下文路径，用于错误定位

        Returns:
            处理后的数据和占位符映射字典
        """
        self.placeholder_map.clear()
        self.placeholder_counter = 0

        protected_data = self._protect_recursive(data, context_path)
        return protected_data, self.placeholder_map

    def restore_jinja_syntax(self, data: Any, placeholder_map: Dict[str, Jinja2Placeholder]) -> Any:
        """
        恢复Jinja2语法

        Args:
            data: 包含占位符的数据
            placeholder_map: 占位符映射字典

        Returns:
            恢复了Jinja2语法的数据
        """
        return self._restore_recursive(data, placeholder_map)

    def json_to_yaml(self, json_data: Dict) -> str:
        """
        将JSON数据转换为YAML格式字符串

        Args:
            json_data: JSON数据字典

        Returns:
            YAML格式字符串
        """
        try:
            # 保护Jinja2语法
            protected_json, placeholder_map = self.protect_jinja_syntax(json_data)

            # 转换为YAML
            yaml_content = yaml.dump(
                protected_json,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
                sort_keys=False,
                Dumper=yaml.SafeDumper
            )

            # 恢复Jinja2语法
            yaml_lines = yaml_content.split('\n')
            restored_lines = []

            for line in yaml_lines:
                restored_line = self._restore_jinja_in_line(line, placeholder_map)
                restored_lines.append(restored_line)

            yaml_with_jinja = '\n'.join(restored_lines)

            logger.info(f"Successfully converted JSON to YAML ({len(yaml_with_jinja)} chars)")
            return yaml_with_jinja

        except Exception as e:
            logger.error(f"Failed to convert JSON to YAML: {e}")
            raise

    def yaml_to_json(self, yaml_content: str) -> Dict[str, Any]:
        """
        将YAML内容转换为JSON字典

        Args:
            yaml_content: YAML格式字符串

        Returns:
            JSON数据字典
        """
        try:
            # 保护Jinja2语法
            placeholder_map = self._extract_jinja_from_yaml(yaml_content)
            protected_yaml = self._protect_yaml_content(yaml_content, placeholder_map)

            # 解析YAML
            parsed_data = yaml.safe_load(protected_yaml)

            # 恢复Jinja2语法
            restored_data = self.restore_jinja_syntax(parsed_data, placeholder_map)

            logger.info(f"Successfully converted YAML to JSON ({len(str(restored_data))} chars)")
            return restored_data

        except Exception as e:
            logger.error(f"Failed to convert YAML to JSON: {e}")
            raise

    def _protect_recursive(self, data: Any, context_path: str = "") -> Any:
        """递归保护Jinja2语法"""

        if isinstance(data, dict):
            protected = {}
            for key, value in data.items():
                new_context = f"{context_path}.{key}" if context_path else key
                protected[key] = self._protect_recursive(value, new_context)
            return protected

        elif isinstance(data, list):
            protected = []
            for i, item in enumerate(data):
                new_context = f"{context_path}[{i}]" if context_path else f"[{i}]"
                protected.append(self._protect_recursive(item, new_context))
            return protected

        elif isinstance(data, str):
            return self._protect_string(data, context_path)

        else:
            return data

    def _protect_string(self, text: str, context_path: str) -> str:
        """保护字符串中的Jinja2语法"""
        if not isinstance(text, str):
            return text

        result = text
        replacements = []

        # 收集所有需要替换的Jinja2语法
        for pattern, jinja_type in [
            (self.variable_pattern, 'variable'),
            (self.statement_pattern, 'statement'),
            (self.comment_pattern, 'comment')
        ]:
            for match in pattern.finditer(text):
                original_content = match.group(0)

                # 特殊处理Jinja2注释：转换为YAML注释
                if jinja_type == 'comment':
                    comment_content = match.group(1).strip()
                    original_content = f"# {comment_content}"

                replacements.append((match.start(), match.end(), match.group(0), jinja_type, original_content))

        # 按位置排序，从后往前替换，避免位置偏移
        replacements.sort(key=lambda x: x[0], reverse=True)

        # 执行替换
        for start, end, original_content, jinja_type, processed_content in replacements:
            placeholder_id = self._create_placeholder(processed_content, jinja_type, context_path)
            result = result[:start] + placeholder_id + result[end:]

        return result

    def _create_placeholder(self, content: str, jinja_type: str, location: str) -> str:
        """创建占位符"""
        self.placeholder_counter += 1
        placeholder_id = f"__JINJA_PLACEHOLDER_{self.placeholder_counter}__"

        placeholder_info = Jinja2Placeholder(
            id=placeholder_id,
            original_content=content,
            placeholder=placeholder_id,
            type=jinja_type,
            location=location
        )

        self.placeholder_map[placeholder_id] = placeholder_info

        return placeholder_id

    def _restore_recursive(self, data: Any, placeholder_map: Dict[str, Jinja2Placeholder]) -> Any:
        """递归恢复Jinja2语法"""

        if isinstance(data, dict):
            restored = {}
            for key, value in data.items():
                restored[key] = self._restore_recursive(value, placeholder_map)
            return restored

        elif isinstance(data, list):
            restored = []
            for item in data:
                restored.append(self._restore_recursive(item, placeholder_map))
            return restored

        elif isinstance(data, str):
            # 检查是否是占位符
            if data in placeholder_map:
                placeholder_info = placeholder_map[data]
                return placeholder_info.original_content
            else:
                return data

        else:
            return data

    def _extract_jinja_from_yaml(self, yaml_content: str) -> Dict[str, Jinja2Placeholder]:
        """从YAML内容中提取Jinja2语法"""
        placeholder_map = {}
        lines = yaml_content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # 在YAML行中查找Jinja2语法
            for match in self.variable_pattern.finditer(line):
                placeholder_id = f"__JINJA_PLACEHOLDER_{len(placeholder_map) + 1}__"
                placeholder_map[placeholder_id] = Jinja2Placeholder(
                    id=placeholder_id,
                    original_content=match.group(0),
                    placeholder=placeholder_id,
                    type='variable',
                    location=f"line:{line_num}"
                )

            for match in self.statement_pattern.finditer(line):
                placeholder_id = f"__JINJA_PLACEHOLDER_{len(placeholder_map) + 1}__"
                placeholder_map[placeholder_id] = Jinja2Placeholder(
                    id=placeholder_id,
                    original_content=match.group(0),
                    placeholder=placeholder_id,
                    type='statement',
                    location=f"line:{line_num}"
                )

        return placeholder_map

    def _protect_yaml_content(self, yaml_content: str, placeholder_map: Dict[str, Jinja2Placeholder]) -> str:
        """保护YAML内容中的Jinja2语法"""
        protected_content = yaml_content

        for placeholder_info in placeholder_map.values():
            protected_content = protected_content.replace(
                placeholder_info.original_content,
                placeholder_info.placeholder
            )

        return protected_content

    def _restore_jinja_in_line(self, line: str, placeholder_map: Dict[str, Jinja2Placeholder]) -> str:
        """在单行中恢复Jinja2语法"""
        restored_line = line

        for placeholder_info in placeholder_map.values():
            if placeholder_info.placeholder in restored_line:
                restored_line = restored_line.replace(
                    placeholder_info.placeholder,
                    placeholder_info.original_content
                )

        return restored_line

    def generate_yaml_schema(self, yaml_data: Any,
                           jinja_placeholders: Dict[str, Jinja2Placeholder] = None) -> Dict[str, Any]:
        """
        生成YAML schema

        Args:
            yaml_data: YAML数据
            jinja_placeholders: Jinja2占位符映射

        Returns:
            YAML schema字典
        """
        if jinja_placeholders is None:
            jinja_placeholders = {}

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Protocol Template Schema",
            "type": "object",
            "description": "Generated schema for YAML protocol template"
        }

        # 递归生成schema属性
        properties = self._generate_schema_properties(yaml_data, jinja_placeholders)
        schema["properties"] = properties

        # 确定必需字段
        required_fields = []
        for name, prop_schema in properties.items():
            if not prop_schema.get("optional", False):
                required_fields.append(name)

        if required_fields:
            schema["required"] = required_fields

        return schema

    def _generate_schema_properties(self, data: Any,
                                  jinja_placeholders: Dict[str, Jinja2Placeholder]) -> Dict[str, Any]:
        """递归生成schema属性"""
        properties = {}

        if isinstance(data, dict):
            for key, value in data.items():
                prop_schema = self._generate_value_schema(value, jinja_placeholders)

                # 检查值是否为Jinja2占位符
                if self._is_jinja_placeholder(value, jinja_placeholders):
                    prop_schema = {
                        "type": "string",
                        "description": "Jinja2 template content",
                        "jinja2": True,
                        "optional": True
                    }

                properties[key] = prop_schema

        elif isinstance(data, list):
            if data:
                item_schema = self._generate_value_schema(data[0], jinja_placeholders)
                properties["items"] = {
                    "type": "array",
                    "items": item_schema,
                    "minItems": len(data) if len(data) > 1 else None
                }

        return properties

    def _generate_value_schema(self, value: Any, jinja_placeholders: Dict[str, Jinja2Placeholder]) -> Dict[str, Any]:
        """生成单个值的schema"""
        # 检查Jinja2占位符
        if self._is_jinja_placeholder(value, jinja_placeholders):
            return {
                "type": "string",
                "description": "Jinja2 template content",
                "jinja2": True,
                "optional": True
            }

        # 根据值类型生成schema
        if isinstance(value, dict):
            properties = self._generate_schema_properties(value, jinja_placeholders)
            schema = {"type": "object", "properties": properties}

            required_fields = [name for name, prop in properties.items()
                             if not prop.get("optional", False)]
            if required_fields:
                schema["required"] = required_fields

            return schema

        elif isinstance(value, list):
            if value:
                items_schema = self._generate_value_schema(value[0], jinja_placeholders)
                return {
                    "type": "array",
                    "items": items_schema,
                    "minItems": len(value) if len(value) > 1 else None
                }
            else:
                return {"type": "array", "items": {}}

        else:
            # 基本类型
            return {
                "type": self._get_json_schema_type(value),
                "enum": [value] if value is not None else None
            }

    def _is_jinja_placeholder(self, value: Any, jinja_placeholders: Dict[str, Jinja2Placeholder]) -> bool:
        """检查值是否为Jinja2占位符"""
        if not isinstance(value, str):
            return False

        for placeholder_info in jinja_placeholders.values():
            if value == placeholder_info.placeholder:
                return True

        return False

    def _get_json_schema_type(self, value: Any) -> str:
        """获取JSON Schema类型"""
        if isinstance(value, str):
            return "string"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, bool):
            return "boolean"
        elif value is None:
            return "null"
        else:
            return "string"  # 默认为字符串

    def extract_yaml_paths(self, yaml_data: Any,
                          placeholder_map: Dict[str, Jinja2Placeholder]) -> Dict[str, List[str]]:
        """
        提取所有Jinja2变量的YAML路径

        Args:
            yaml_data: YAML数据
            placeholder_map: 占位符映射

        Returns:
            变量名到YAML路径列表的映射
        """
        variable_paths = {}

        # 从占位符中提取变量名
        for placeholder_info in placeholder_map.values():
            if placeholder_info.type == 'variable':
                # 从Jinja2表达式中提取变量名
                var_names = self._extract_variable_names(placeholder_info.original_content)
                location = placeholder_info.location or ""

                for var_name in var_names:
                    if var_name not in variable_paths:
                        variable_paths[var_name] = []

                    if location not in variable_paths[var_name]:
                        variable_paths[var_name].append(location)

        return variable_paths

    def _extract_variable_names(self, jinja_expression: str) -> List[str]:
        """从Jinja2表达式中提取变量名"""
        # 简单的变量名提取（可以进一步优化）
        content = jinja_expression.strip()

        # 移除 {{ 和 }}
        content = content[2:-2].strip()

        # 处理过滤器
        if '|' in content:
            content = content.split('|')[0].strip()

        # 处理函数调用
        if '(' in content:
            content = content.split('(')[0].strip()

        # 清理空格
        var_name = content.strip()

        return [var_name] if var_name else []

    def get_protected_content_map(self, placeholder_map: Dict[str, Jinja2Placeholder]) -> Dict[str, str]:
        """获取受保护内容的映射"""
        return {
            placeholder_info.placeholder: placeholder_info.original_content
            for placeholder_info in placeholder_map.values()
        }

    def validate_yaml_structure(self, yaml_content: str) -> Tuple[bool, List[str]]:
        """验证YAML结构是否正确"""
        errors = []

        try:
            # 尝试解析YAML
            yaml.safe_load(yaml_content)
            return True, errors
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {str(e)}")
            return False, errors
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            return False, errors