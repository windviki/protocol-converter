#!/usr/bin/env python3
"""
YAML协议模板验证工具
验证YAML格式协议模板的正确性和完整性
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import yaml

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.yaml_processor import YamlProcessor
from utils.yaml_schema import YamlSchemaGenerator
from utils.variable_mapper import VariableMapper
from utils.yaml_path import YamlPath, PathError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationIssue:
    """验证问题"""
    severity: str  # 'error', 'warning', 'info'
    message: str
    path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """验证结果"""
    file_path: str
    is_valid: bool
    issues: List[ValidationIssue]
    statistics: Dict[str, Any]
    processing_time: float = 0.0

class YamlValidator:
    """YAML验证器"""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.yaml_processor = YamlProcessor()
        self.schema_generator = YamlSchemaGenerator()
        self.variable_mapper = VariableMapper()

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        验证单个YAML文件

        Args:
            file_path: YAML文件路径

        Returns:
            验证结果
        """
        import time
        start_time = time.time()

        issues = []
        statistics = {}

        try:
            logger.info(f"Validating {file_path.name}")

            # 读取YAML文件
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()

            # 检查是否是纯模板文件（没有metadata）
            if 'metadata:' not in yaml_content and 'template:' not in yaml_content:
                # 纯YAML模板文件
                self._validate_pure_template(yaml_content, file_path, issues)
            else:
                # 完整的YAML文件（包含metadata）
                protected_content, placeholder_map = self.yaml_processor._extract_jinja_from_yaml(yaml_content)
                protected_yaml = self.yaml_processor._protect_yaml_content(yaml_content, placeholder_map)
                yaml_data = yaml.safe_load(protected_yaml)

                # 基本结构验证
                structure_issues = self._validate_structure(yaml_data, file_path)
                issues.extend(structure_issues)

                if not structure_issues or any(issue.severity == 'error' for issue in structure_issues):
                    # 如果没有结构性错误，继续详细验证
                    metadata = yaml_data.get('metadata', {})
                    template = yaml_data.get('template')
                    schema = yaml_data.get('schema')
                    variable_mapping = yaml_data.get('variable_mapping')
                    jinja_placeholders = yaml_data.get('jinja_placeholders', {})

                    # 验证元数据
                    metadata_issues = self._validate_metadata(metadata, file_path)
                    issues.extend(metadata_issues)

                    # 验证模板内容
                    if template:
                        template_issues = self._validate_template(template, jinja_placeholders, file_path)
                        issues.extend(template_issues)

                    # 验证schema
                    if schema:
                        schema_issues = self._validate_schema(schema, file_path)
                        issues.extend(schema_issues)

                        # 使用schema验证模板
                        if template:
                            schema_validation_issues = self._validate_template_with_schema(template, schema, file_path)
                            issues.extend(schema_validation_issues)

                    # 验证变量映射
                    if variable_mapping:
                        mapping_issues = self._validate_variable_mapping(variable_mapping, template, file_path)
                        issues.extend(mapping_issues)

            # 计算统计信息
            if 'yaml_data' in locals():
                statistics = self._calculate_statistics(yaml_data, issues)
            else:
                # 对于纯模板文件，使用简化的统计信息
                statistics = {
                    'total_issues': len(issues),
                    'error_count': len([i for i in issues if i.severity == 'error']),
                    'warning_count': len([i for i in issues if i.severity == 'warning']),
                    'info_count': len([i for i in issues if i.severity == 'info'])
                }

            processing_time = time.time() - start_time
            is_valid = not any(issue.severity == 'error' for issue in issues)

            if is_valid:
                logger.info(f"✅ {file_path.name} is valid")
            else:
                logger.warning(f"❌ {file_path.name} has {len([i for i in issues if i.severity == 'error'])} errors")

            return ValidationResult(
                file_path=str(file_path),
                is_valid=is_valid,
                issues=issues,
                statistics=statistics,
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to validate {file_path.name}: {e}")
            return ValidationResult(
                file_path=str(file_path),
                is_valid=False,
                issues=[ValidationIssue(
                    severity='error',
                    message=f"Validation failed: {str(e)}",
                    path=str(file_path)
                )],
                statistics={},
                processing_time=processing_time
            )

    def validate_directory(self, directory_path: Path) -> List[ValidationResult]:
        """
        验证目录中的所有YAML文件

        Args:
            directory_path: 目录路径

        Returns:
            验证结果列表
        """
        yaml_files = list(directory_path.rglob("*.yaml"))
        logger.info(f"Found {len(yaml_files)} YAML files to validate")

        results = []
        for yaml_file in yaml_files:
            result = self.validate_file(yaml_file)
            results.append(result)

        return results

    def _validate_pure_template(self, yaml_content: str, file_path: Path, issues: List[ValidationIssue]) -> None:
        """验证纯YAML模板文件"""
        try:
            # 保护Jinja2语法
            placeholder_map = self.yaml_processor._extract_jinja_from_yaml(yaml_content)
            protected_yaml = self.yaml_processor._protect_yaml_content(yaml_content, placeholder_map)

            # 尝试解析YAML
            yaml_data = yaml.safe_load(protected_yaml)

            # 验证Jinja2语法
            jinja_issues = self._validate_jinja_syntax(yaml_content, placeholder_map, file_path)
            issues.extend(jinja_issues)

            # 检查动态数组标记
            array_issues = self._validate_array_markers(yaml_data, file_path)
            issues.extend(array_issues)

            # 基本YAML语法检查
            if not isinstance(yaml_data, dict):
                issues.append(ValidationIssue(
                    severity='error',
                    message="YAML template must be a dictionary/object",
                    path=str(file_path),
                    suggestion="Ensure the YAML template starts with a top-level object"
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity='error',
                message=f"Failed to parse YAML template: {str(e)}",
                path=str(file_path),
                suggestion="Check YAML syntax and Jinja2 expressions"
            ))

    def _validate_structure(self, yaml_data: Any, file_path: Path) -> List[ValidationIssue]:
        """验证YAML文件基本结构"""
        issues = []

        if not isinstance(yaml_data, dict):
            issues.append(ValidationIssue(
                severity='error',
                message="YAML root must be a dictionary/object",
                path=str(file_path),
                suggestion="Ensure the YAML file starts with a top-level object"
            ))
            return issues

        # 检查必需的顶级字段
        required_fields = ['metadata', 'template']
        for field in required_fields:
            if field not in yaml_data:
                severity = 'error' if self.strict_mode else 'warning'
                issues.append(ValidationIssue(
                    severity=severity,
                    message=f"Missing required field: {field}",
                    path=f"$.{field}",
                    suggestion=f"Add the '{field}' section to the YAML file"
                ))

        return issues

    def _validate_metadata(self, metadata: Dict[str, Any], file_path: Path) -> List[ValidationIssue]:
        """验证元数据"""
        issues = []

        if not isinstance(metadata, dict):
            issues.append(ValidationIssue(
                severity='error',
                message="Metadata must be a dictionary/object",
                path="$.metadata",
                suggestion="Ensure metadata is properly formatted as a YAML object"
            ))
            return issues

        # 检查必需的元数据字段
        required_metadata_fields = ['protocol_id', 'family', 'conversion_timestamp']
        for field in required_metadata_fields:
            if field not in metadata:
                issues.append(ValidationIssue(
                    severity='warning',
                    message=f"Missing metadata field: {field}",
                    path=f"$.metadata.{field}",
                    suggestion=f"Add '{field}' to the metadata section"
                ))

        # 验证protocol_id格式
        if 'protocol_id' in metadata:
            protocol_id = metadata['protocol_id']
            if not isinstance(protocol_id, str) or '-' not in protocol_id:
                issues.append(ValidationIssue(
                    severity='warning',
                    message="Invalid protocol_id format",
                    path="$.metadata.protocol_id",
                    value=protocol_id,
                    suggestion="Protocol ID should follow the pattern 'FAMILY-NUMBER' (e.g., 'A-1')"
                ))

        # 验证时间戳格式
        if 'conversion_timestamp' in metadata:
            timestamp = metadata['conversion_timestamp']
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                issues.append(ValidationIssue(
                    severity='warning',
                    message="Invalid timestamp format",
                    path="$.metadata.conversion_timestamp",
                    value=timestamp,
                    suggestion="Use ISO 8601 format (e.g., '2024-01-01T12:00:00')"
                ))

        return issues

    def _validate_template(self, template: Any, jinja_placeholders: Dict, file_path: Path) -> List[ValidationIssue]:
        """验证模板内容"""
        issues = []

        if not isinstance(template, dict):
            issues.append(ValidationIssue(
                severity='error',
                message="Template must be a dictionary/object",
                path="$.template",
                suggestion="Ensure template is properly formatted as a YAML object"
            ))
            return issues

        # 检查Jinja2语法
        template_str = yaml.dump(template, default_flow_style=False)
        jinja_issues = self._validate_jinja_syntax(template_str, jinja_placeholders, file_path)
        issues.extend(jinja_issues)

        # 检查动态数组标记
        array_issues = self._validate_array_markers(template, file_path)
        issues.extend(array_issues)

        return issues

    def _validate_jinja_syntax(self, content: str, jinja_placeholders: Dict, file_path: Path) -> List[ValidationIssue]:
        """验证Jinja2语法"""
        issues = []

        # 检查未匹配的括号
        open_braces = content.count('{{')
        close_braces = content.count('}}')
        if open_braces != close_braces:
            issues.append(ValidationIssue(
                severity='error',
                message=f"Mismatched Jinja2 variable brackets: {open_braces} '{{' vs {close_braces} '}}'",
                path=str(file_path),
                suggestion="Check for missing or extra brackets in Jinja2 expressions"
            ))

        open_blocks = content.count('{%')
        close_blocks = content.count('%}')
        if open_blocks != close_blocks:
            issues.append(ValidationIssue(
                severity='error',
                message=f"Mismatched Jinja2 block brackets: {open_blocks} '{{%' vs {close_blocks} '%}}'",
                path=str(file_path),
                suggestion="Check for missing or extra block delimiters"
            ))

        # 检查常见的Jinja2语法错误
        common_errors = [
            (r'\{\{\s*\}\}', "Empty Jinja2 variable expression"),
            (r'\{\%\s*\%\}', "Empty Jinja2 block"),
            (r'\{\{\s*[^}]*$', "Unclosed Jinja2 variable"),
            (r'\{\%\s*[^%]*$', "Unclosed Jinja2 block")
        ]

        import re
        for pattern, message in common_errors:
            if re.search(pattern, content):
                issues.append(ValidationIssue(
                    severity='warning',
                    message=message,
                    path=str(file_path),
                    suggestion="Review and fix the Jinja2 syntax"
                ))

        return issues

    def _validate_array_markers(self, template: Any, file_path: Path, current_path: str = "$.template") -> List[ValidationIssue]:
        """验证动态数组标记"""
        issues = []

        if isinstance(template, dict):
            for key, value in template.items():
                new_path = f"{current_path}.{key}"
                issues.extend(self._validate_array_markers(value, file_path, new_path))

        elif isinstance(template, list):
            for i, item in enumerate(template):
                new_path = f"{current_path}[{i}]"
                if isinstance(item, str) and "array_dynamic: true" in item:
                    # 验证动态数组标记格式
                    if not item.strip() == "{# array_dynamic: true #}":
                        issues.append(ValidationIssue(
                            severity='warning',
                            message="Invalid dynamic array marker format",
                            path=new_path,
                            value=item,
                            suggestion="Use exact format: '{# array_dynamic: true #}'"
                        ))
                else:
                    issues.extend(self._validate_array_markers(item, file_path, new_path))

        return issues

    def _validate_schema(self, schema: Dict[str, Any], file_path: Path) -> List[ValidationIssue]:
        """验证schema定义"""
        issues = []

        if not isinstance(schema, dict):
            issues.append(ValidationIssue(
                severity='error',
                message="Schema must be a dictionary/object",
                path="$.schema",
                suggestion="Ensure schema is properly formatted as a YAML object"
            ))
            return issues

        # 检查必需的schema字段
        if '$schema' not in schema:
            issues.append(ValidationIssue(
                severity='warning',
                message="Missing JSON Schema $schema field",
                path="$.schema.$schema",
                suggestion="Add '$schema: http://json-schema.org/draft-07/schema#' to schema"
            ))

        if 'type' not in schema:
            issues.append(ValidationIssue(
                severity='error',
                message="Missing schema type field",
                path="$.schema.type",
                suggestion="Add 'type: object' to schema"
            ))
        elif schema['type'] != 'object':
            issues.append(ValidationIssue(
                severity='warning',
                message="Schema type should be 'object' for protocol templates",
                path="$.schema.type",
                value=schema['type'],
                suggestion="Use 'type: object' for protocol templates"
            ))

        return issues

    def _validate_template_with_schema(self, template: Any, schema: Dict[str, Any], file_path: Path) -> List[ValidationIssue]:
        """使用schema验证模板"""
        issues = []

        try:
            # 保护Jinja2语法
            protected_template, placeholder_map = self.yaml_processor.protect_jinja_syntax(template)

            # 使用schema验证
            validation_result = self.schema_generator.validate_data(protected_template, schema)

            if not validation_result.is_valid:
                for error in validation_result.errors:
                    issues.append(ValidationIssue(
                        severity='error',
                        message=f"Schema validation error: {error}",
                        path="$.template",
                        suggestion="Fix the template structure to match the schema"
                    ))

            for warning in validation_result.warnings:
                issues.append(ValidationIssue(
                    severity='warning',
                    message=f"Schema validation warning: {warning}",
                    path="$.template"
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity='error',
                message=f"Schema validation failed: {str(e)}",
                path="$.template",
                suggestion="Check schema and template format"
            ))

        return issues

    def _validate_variable_mapping(self, variable_mapping: Dict[str, Any], template: Any, file_path: Path) -> List[ValidationIssue]:
        """验证变量映射"""
        issues = []

        if not isinstance(variable_mapping, dict):
            issues.append(ValidationIssue(
                severity='error',
                message="Variable mapping must be a dictionary/object",
                path="$.variable_mapping",
                suggestion="Ensure variable_mapping is properly formatted"
            ))
            return issues

        # 检查必需的变量映射字段
        required_fields = ['regular_variables', 'special_variables', 'variable_paths']
        for field in required_fields:
            if field not in variable_mapping:
                issues.append(ValidationIssue(
                    severity='warning',
                    message=f"Missing variable mapping field: {field}",
                    path=f"$.variable_mapping.{field}",
                    suggestion=f"Add '{field}' to variable mapping"
                ))

        # 验证变量列表格式
        for list_field in ['regular_variables', 'special_variables']:
            if list_field in variable_mapping:
                if not isinstance(variable_mapping[list_field], list):
                    issues.append(ValidationIssue(
                        severity='error',
                        message=f"Variable list '{list_field}' must be an array",
                        path=f"$.variable_mapping.{list_field}",
                        suggestion="Format as a YAML list"
                    ))

        # 验证变量路径映射
        if 'variable_paths' in variable_mapping:
            variable_paths = variable_mapping['variable_paths']
            if not isinstance(variable_paths, dict):
                issues.append(ValidationIssue(
                    severity='error',
                    message="Variable paths must be a dictionary/object",
                    path="$.variable_mapping.variable_paths",
                    suggestion="Format as a YAML object mapping variable names to path lists"
                ))
            else:
                for var_name, paths in variable_paths.items():
                    if not isinstance(paths, list):
                        issues.append(ValidationIssue(
                            severity='warning',
                            message=f"Variable paths for '{var_name}' must be an array",
                            path=f"$.variable_mapping.variable_paths.{var_name}",
                            suggestion="Format as a YAML list of paths"
                        ))

        return issues

    def _calculate_statistics(self, yaml_data: Dict[str, Any], issues: List[ValidationIssue]) -> Dict[str, Any]:
        """计算统计信息"""
        stats = {}

        # 基本统计
        template = yaml_data.get('template', {})
        schema = yaml_data.get('schema', {})
        variable_mapping = yaml_data.get('variable_mapping', {})

        stats['template_size'] = len(str(template))
        stats['schema_properties'] = len(schema.get('properties', {}))
        stats['total_variables'] = len(variable_mapping.get('regular_variables', [])) + len(variable_mapping.get('special_variables', []))
        stats['jinja_placeholders'] = len(yaml_data.get('jinja_placeholders', {}))

        # 问题统计
        stats['total_issues'] = len(issues)
        stats['error_count'] = len([i for i in issues if i.severity == 'error'])
        stats['warning_count'] = len([i for i in issues if i.severity == 'warning'])
        stats['info_count'] = len([i for i in issues if i.severity == 'info'])

        return stats

    def generate_validation_report(self, results: List[ValidationResult], output_file: str = None) -> str:
        """生成验证报告"""
        lines = []
        lines.append("# YAML Validation Report")
        lines.append("=" * 50)
        lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 总体统计
        total_files = len(results)
        valid_files = len([r for r in results if r.is_valid])
        invalid_files = total_files - valid_files
        total_issues = sum(len(r.issues) for r in results)
        total_errors = sum(r.statistics.get('error_count', 0) for r in results)
        total_warnings = sum(r.statistics.get('warning_count', 0) for r in results)

        lines.append("## Summary")
        lines.append(f"- Total files: {total_files}")
        lines.append(f"- Valid files: {valid_files}")
        lines.append(f"- Invalid files: {invalid_files}")
        lines.append(f"- Total issues: {total_issues}")
        lines.append(f"- Total errors: {total_errors}")
        lines.append(f"- Total warnings: {total_warnings}")
        lines.append(f"- Success rate: {valid_files/total_files*100:.1f}%")
        lines.append("")

        # 详细结果
        lines.append("## Detailed Results")
        for result in results:
            file_name = Path(result.file_path).name
            status = "✅ Valid" if result.is_valid else "❌ Invalid"
            lines.append(f"### {file_name} - {status}")
            lines.append(f"- Processing time: {result.processing_time:.3f}s")
            lines.append(f"- Issues: {len(result.issues)} (Errors: {result.statistics.get('error_count', 0)}, Warnings: {result.statistics.get('warning_count', 0)})")

            if result.statistics.get('total_variables', 0) > 0:
                lines.append(f"- Variables: {result.statistics['total_variables']} total")

            # 显示问题
            if result.issues:
                lines.append("  Issues:")
                for issue in result.issues[:5]:  # 只显示前5个问题
                    icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "•")
                    lines.append(f"  {icon} {issue.message}")
                    if issue.path:
                        lines.append(f"     Path: {issue.path}")
                    if issue.suggestion:
                        lines.append(f"     Suggestion: {issue.suggestion}")

                if len(result.issues) > 5:
                    lines.append(f"     ... and {len(result.issues) - 5} more issues")

            lines.append("")

        report_content = "\n".join(lines)

        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Validation report saved to {output_file}")

        return report_content

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Validate YAML protocol templates")
    parser.add_argument("path", help="Path to YAML file or directory to validate")
    parser.add_argument("-r", "--report", help="Output file for validation report", default="./validation_report.md")
    parser.add_argument("--strict", action="store_true", help="Enable strict validation mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        validator = YamlValidator(strict_mode=args.strict)
        path = Path(args.path)

        if path.is_file():
            results = [validator.validate_file(path)]
        elif path.is_dir():
            results = validator.validate_directory(path)
        else:
            logger.error(f"Path does not exist: {args.path}")
            sys.exit(1)

        # 生成报告
        report_content = validator.generate_validation_report(results, args.report)
        print(report_content)

        # 返回适当的退出码
        invalid_count = len([r for r in results if not r.is_valid])
        if invalid_count > 0:
            logger.warning(f"Validation completed with {invalid_count} invalid files")
            sys.exit(1)
        else:
            logger.info("All files are valid")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()