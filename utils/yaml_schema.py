"""
YAML Schema生成器和验证器
提供基于YAML数据结构的schema生成和验证功能
"""

from typing import Any, Dict, List, Set, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from .yaml_path import YamlPath, PathError

logger = logging.getLogger(__name__)

class SchemaType(Enum):
    """Schema类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"

@dataclass
class SchemaField:
    """Schema字段定义"""
    name: str
    type: SchemaType
    required: bool = True
    enum_values: Optional[List[Any]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    properties: Optional[Dict[str, 'SchemaField']] = None
    items: Optional['SchemaField'] = None
    pattern: Optional[str] = None  # 正则表达式模式
    format: Optional[str] = None   # 格式（如 date-time, email 等）
    description: Optional[str] = None

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    matched_paths: List[str]
    unmatched_paths: List[str]
    validation_details: Optional[Dict[str, Any]] = None

    def get_summary(self) -> str:
        """获取验证结果摘要"""
        if self.is_valid:
            return f"✓ Validation passed with {len(self.warnings)} warnings"
        else:
            return f"✗ Validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings"

    def get_error_report(self) -> str:
        """获取详细错误报告"""
        lines = [self.get_summary()]

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  ❌ {error}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠️  {warning}")

        if self.matched_paths:
            lines.append(f"\nMatched paths ({len(self.matched_paths)}):")
            for path in sorted(self.matched_paths):
                lines.append(f"  ✓ {path}")

        if self.unmatched_paths:
            lines.append(f"\nUnmatched paths ({len(self.unmatched_paths)}):")
            for path in sorted(self.unmatched_paths):
                lines.append(f"  ✗ {path}")

        return "\n".join(lines)

class YamlSchemaGenerator:
    """YAML Schema生成器"""

    def __init__(self):
        self.type_mapping = {
            str: SchemaType.STRING,
            int: SchemaType.INTEGER,
            float: SchemaType.NUMBER,
            bool: SchemaType.BOOLEAN,
            list: SchemaType.ARRAY,
            dict: SchemaType.OBJECT,
            type(None): SchemaType.NULL
        }

    def generate_schema(self, yaml_data: Any,
                       jinja_placeholders: Dict[str, str] = None,
                       schema_title: str = "YAML Data Schema") -> Dict[str, Any]:
        """
        生成YAML schema

        Args:
            yaml_data: YAML数据
            jinja_placeholders: Jinja2占位符映射
            schema_title: schema标题

        Returns:
            YAML schema字典
        """
        if jinja_placeholders is None:
            jinja_placeholders = {}

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": schema_title,
            "type": "object",
            "description": "Auto-generated schema from YAML data"
        }

        # 递归生成schema
        properties = self._generate_properties(yaml_data, jinja_placeholders)
        schema["properties"] = properties

        # 确定必需字段
        required_fields = []
        for name, field in properties.items():
            if not field.get("optional", False):
                required_fields.append(name)

        if required_fields:
            schema["required"] = required_fields

        # 添加额外信息
        schema["additionalProperties"] = True  # 允许额外属性

        logger.info(f"Generated schema with {len(properties)} properties")
        return schema

    def _generate_properties(self, data: Any,
                           jinja_placeholders: Dict[str, str]) -> Dict[str, Any]:
        """递归生成属性schema"""
        properties = {}

        if isinstance(data, dict):
            for key, value in data.items():
                prop_schema = self._generate_value_schema(value, jinja_placeholders)

                # 检查是否为Jinja2占位符
                if self._is_jinja_placeholder(str(value), jinja_placeholders):
                    prop_schema = {
                        "type": "string",
                        "description": "Jinja2 template placeholder",
                        "jinja2": True,
                        "optional": True  # Jinja2字段通常是可选的
                    }

                properties[key] = prop_schema

        elif isinstance(data, list):
            if data:
                item_schema = self._generate_value_schema(data[0], jinja_placeholders)
                properties["items"] = {
                    "type": "array",
                    "items": item_schema
                }

        return properties

    def _generate_value_schema(self, value: Any,
                             jinja_placeholders: Dict[str, str]) -> Dict[str, Any]:
        """生成单个值的schema"""
        value_str = str(value)

        # 检查Jinja2占位符
        if self._is_jinja_placeholder(value_str, jinja_placeholders):
            return {
                "type": "string",
                "description": "Jinja2 template placeholder",
                "jinja2": True,
                "optional": True
            }

        # 根据值类型生成schema
        if isinstance(value, dict):
            properties = self._generate_properties(value, jinja_placeholders)
            schema = {"type": "object", "properties": properties}

            required_fields = [name for name, prop in properties.items()
                             if not prop.get("optional", False)]
            if required_fields:
                schema["required"] = required_fields

            return schema

        elif isinstance(value, list):
            if value:
                # 分析所有元素的共同类型
                items_schemas = []
                for item in value:
                    item_schema = self._generate_value_schema(item, jinja_placeholders)
                    items_schemas.append(item_schema)

                # 合并schema
                merged_items_schema = self._merge_schemas(items_schemas)

                return {
                    "type": "array",
                    "items": merged_items_schema,
                    "minItems": len(value) if len(value) > 1 else None
                }
            else:
                return {"type": "array", "items": {}}

        else:
            # 基本类型
            schema = {
                "type": self._get_json_schema_type(value)
            }

            # 添加枚举值
            if value is not None:
                schema["enum"] = [value]

            # 添加约束
            if isinstance(value, str):
                if len(value) > 0:
                    schema["minLength"] = 1
                schema["maxLength"] = len(value)

            return schema

    def _merge_schemas(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个schema"""
        if not schemas:
            return {}

        if len(schemas) == 1:
            return schemas[0]

        # 找出共同类型
        types = set()
        for schema in schemas:
            schema_type = schema.get("type", "any")
            types.add(schema_type)

        merged = {}

        if len(types) == 1:
            merged["type"] = types.pop()
        else:
            merged["anyOf"] = [{"type": t} for t in types]

        # 合并其他属性
        all_keys = set()
        for schema in schemas:
            all_keys.update(schema.keys())

        for key in all_keys:
            if key == "type":
                continue

            values = [schema.get(key) for schema in schemas if key in schema]
            if len(set(str(v) for v in values)) == 1:
                merged[key] = values[0]

        return merged

    def _is_jinja_placeholder(self, value: str, jinja_placeholders: Dict[str, str]) -> bool:
        """检查是否为Jinja2占位符"""
        return value in jinja_placeholders.values()

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

    def validate_data(self, data: Any, schema: Dict[str, Any],
                     strict_mode: bool = False) -> ValidationResult:
        """
        使用schema验证数据

        Args:
            data: 要验证的数据
            schema: schema定义
            strict_mode: 严格模式，禁止额外属性

        Returns:
            验证结果
        """
        errors = []
        warnings = []
        matched_paths = []
        unmatched_paths = []
        validation_details = {}

        # 递归验证
        self._validate_recursive(
            data, schema, "", errors, warnings,
            matched_paths, unmatched_paths, validation_details, strict_mode
        )

        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            matched_paths=matched_paths,
            unmatched_paths=unmatched_paths,
            validation_details=validation_details
        )

        logger.info(f"Validation completed: {result.get_summary()}")
        return result

    def _validate_recursive(self, data: Any, schema: Dict[str, Any],
                          current_path: str, errors: List[str], warnings: List[str],
                          matched_paths: List[str], unmatched_paths: List[str],
                          validation_details: Dict, strict_mode: bool) -> None:
        """递归验证数据结构"""

        # 类型检查
        if "type" in schema:
            expected_type = schema["type"]
            if not self._check_type(data, expected_type):
                errors.append(f"Type mismatch at '{current_path}': expected {expected_type}, got {type(data).__name__}")
                return

        # anyOf 检查
        if "anyOf" in schema:
            any_valid = False
            for sub_schema in schema["anyOf"]:
                sub_errors = []
                self._validate_recursive(
                    data, sub_schema, current_path, sub_errors, warnings,
                    matched_paths, unmatched_paths, validation_details, strict_mode
                )
                if not sub_errors:
                    any_valid = True
                    break

            if not any_valid:
                errors.append(f"Data at '{current_path}' does not match any of the allowed schemas")
            return

        expected_type = schema.get("type", "object")

        if expected_type == "object":
            if not isinstance(data, dict):
                errors.append(f"Expected object at '{current_path}', got {type(data).__name__}")
                return

            properties = schema.get("properties", {})
            required_fields = schema.get("required", [])
            additional_properties = schema.get("additionalProperties", True)

            # 检查必需字段
            for field in required_fields:
                field_path = f"{current_path}.{field}" if current_path else field
                if field not in data:
                    errors.append(f"Required field '{field_path}' is missing")
                    unmatched_paths.append(field_path)
                else:
                    matched_paths.append(field_path)
                    # 递归验证字段
                    if field in properties:
                        self._validate_recursive(
                            data[field], properties[field], field_path,
                            errors, warnings, matched_paths, unmatched_paths,
                            validation_details, strict_mode
                        )

            # 检查可选字段
            for field, value in data.items():
                field_path = f"{current_path}.{field}" if current_path else field

                if field in properties:
                    matched_paths.append(field_path)
                    self._validate_recursive(
                        value, properties[field], field_path,
                        errors, warnings, matched_paths, unmatched_paths,
                        validation_details, strict_mode
                    )
                elif not additional_properties and strict_mode:
                    errors.append(f"Unexpected field '{field_path}' in strict mode")
                else:
                    warnings.append(f"Additional field '{field_path}' not defined in schema")

        elif expected_type == "array":
            if not isinstance(data, list):
                errors.append(f"Expected array at '{current_path}', got {type(data).__name__}")
                return

            items_schema = schema.get("items", {})
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")

            # 数组长度检查
            if min_items is not None and len(data) < min_items:
                errors.append(f"Array at '{current_path}' has {len(data)} items, minimum {min_items}")

            if max_items is not None and len(data) > max_items:
                errors.append(f"Array at '{current_path}' has {len(data)} items, maximum {max_items}")

            # 验证数组元素
            for i, item in enumerate(data):
                item_path = f"{current_path}[{i}]" if current_path else f"[{i}]"
                matched_paths.append(item_path)
                self._validate_recursive(
                    item, items_schema, item_path,
                    errors, warnings, matched_paths, unmatched_paths,
                    validation_details, strict_mode
                )

        # 字符串约束检查
        elif expected_type == "string" and isinstance(data, str):
            min_length = schema.get("minLength")
            max_length = schema.get("maxLength")
            pattern = schema.get("pattern")

            if min_length is not None and len(data) < min_length:
                errors.append(f"String at '{current_path}' has length {len(data)}, minimum {min_length}")

            if max_length is not None and len(data) > max_length:
                errors.append(f"String at '{current_path}' has length {len(data)}, maximum {max_length}")

            if pattern and not re.match(pattern, data):
                errors.append(f"String at '{current_path}' does not match pattern '{pattern}'")

        # 数值约束检查
        elif expected_type in ["integer", "number"] and isinstance(data, (int, float)):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            exclusive_minimum = schema.get("exclusiveMinimum")
            exclusive_maximum = schema.get("exclusiveMaximum")

            if minimum is not None and data < minimum:
                errors.append(f"Number at '{current_path}' is {data}, minimum {minimum}")

            if maximum is not None and data > maximum:
                errors.append(f"Number at '{current_path}' is {data}, maximum {maximum}")

            if exclusive_minimum is not None and data <= exclusive_minimum:
                errors.append(f"Number at '{current_path}' is {data}, must be > {exclusive_minimum}")

            if exclusive_maximum is not None and data >= exclusive_maximum:
                errors.append(f"Number at '{current_path}' is {data}, must be < {exclusive_maximum}")

        # 枚举值检查
        if "enum" in schema:
            if data not in schema["enum"]:
                errors.append(f"Value at '{current_path}' is {data}, allowed values: {schema['enum']}")

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查值类型"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
            "null": type(None)
        }
        expected_python_type = type_mapping.get(expected_type, str)
        return isinstance(value, expected_python_type)

    def generate_schema_report(self, schema: Dict[str, Any]) -> str:
        """生成schema报告"""
        lines = []
        lines.append("YAML Schema Report")
        lines.append("=" * 30)

        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        lines.append(f"Schema Title: {schema.get('title', 'Untitled')}")
        lines.append(f"Properties: {len(properties)}")
        lines.append(f"Required Fields: {len(required_fields)}")

        if properties:
            lines.append("\nProperties:")
            for name, prop_schema in sorted(properties.items()):
                prop_type = prop_schema.get("type", "unknown")
                is_required = name in required_fields
                req_marker = " (required)" if is_required else " (optional)"

                lines.append(f"  - {name}: {prop_type}{req_marker}")

                # 添加额外信息
                if "description" in prop_schema:
                    lines.append(f"    Description: {prop_schema['description']}")

                if "enum" in prop_schema:
                    lines.append(f"    Enum values: {prop_schema['enum']}")

                if prop_type == "array" and "items" in prop_schema:
                    items_type = prop_schema["items"].get("type", "any")
                    lines.append(f"    Items type: {items_type}")

                if prop_type == "object" and "properties" in prop_schema:
                    sub_props = len(prop_schema["properties"])
                    lines.append(f"    Nested properties: {sub_props}")

        return "\n".join(lines)

# 便利函数
def generate_schema(data: Any, jinja_placeholders: Dict[str, str] = None) -> Dict[str, Any]:
    """生成schema的便利函数"""
    generator = YamlSchemaGenerator()
    return generator.generate_schema(data, jinja_placeholders)

def validate_data(data: Any, schema: Dict[str, Any], strict_mode: bool = False) -> ValidationResult:
    """验证数据的便利函数"""
    generator = YamlSchemaGenerator()
    return generator.validate_data(data, schema, strict_mode)

# 需要导入re模块
import re