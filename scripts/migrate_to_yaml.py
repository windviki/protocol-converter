#!/usr/bin/env python3
"""
协议模板批量转换工具
将JSON格式的协议模板批量转换为YAML格式
"""

import os
import json
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

from utils.yaml_processor import YamlProcessor, Jinja2Placeholder
from utils.yaml_schema import YamlSchemaGenerator
from utils.variable_mapper import VariableMapper

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConversionResult:
    """转换结果"""
    source_file: str
    target_file: str
    success: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    processing_time: float = 0.0
    statistics: Dict[str, Any] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.statistics is None:
            self.statistics = {}

@dataclass
class MigrationReport:
    """迁移报告"""
    total_files: int
    successful_conversions: int
    failed_conversions: int
    total_warnings: int
    processing_time: float
    results: List[ConversionResult]
    summary: Dict[str, Any]

class ProtocolMigrator:
    """协议迁移器"""

    def __init__(self, output_dir: str = None, backup: bool = True):
        self.output_dir = output_dir
        self.backup = backup
        self.yaml_processor = YamlProcessor()
        self.schema_generator = YamlSchemaGenerator()
        self.variable_mapper = VariableMapper()

        # 统计信息
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'total_warnings': 0,
            'jinja_variables_found': 0,
            'array_markers_found': 0
        }

    def migrate_directory(self, source_dir: str, output_dir: str = None) -> MigrationReport:
        """
        迁移整个目录的协议文件

        Args:
            source_dir: 源目录路径
            output_dir: 输出目录路径

        Returns:
            迁移报告
        """
        import time
        start_time = time.time()

        source_path = Path(source_dir)
        if not source_path.exists():
            raise ValueError(f"Source directory does not exist: {source_dir}")

        if output_dir:
            self.output_dir = output_dir

        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting migration from {source_dir} to {self.output_dir}")

        # 查找所有JSON文件
        json_files = list(source_path.rglob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files to process")

        results = []
        for json_file in json_files:
            try:
                result = self.migrate_file(json_file, output_path)
                results.append(result)
                self._update_stats(result)
            except Exception as e:
                logger.error(f"Failed to process {json_file}: {e}")
                result = ConversionResult(
                    source_file=str(json_file),
                    target_file="",
                    success=False,
                    error_message=str(e)
                )
                results.append(result)
                self.stats['failed'] += 1

        processing_time = time.time() - start_time

        # 生成报告
        report = MigrationReport(
            total_files=len(json_files),
            successful_conversions=self.stats['successful'],
            failed_conversions=self.stats['failed'],
            total_warnings=self.stats['total_warnings'],
            processing_time=processing_time,
            results=results,
            summary=self._generate_summary()
        )

        logger.info(f"Migration completed: {report.successful_conversions}/{report.total_files} successful "
                   f"in {processing_time:.2f}s")

        return report

    def migrate_file(self, source_file: Path, output_dir: Path) -> ConversionResult:
        """
        迁换单个文件

        Args:
            source_file: 源文件路径
            output_dir: 输出目录路径

        Returns:
            转换结果
        """
        import time
        start_time = time.time()

        try:
            # 读取JSON文件
            with open(source_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            logger.info(f"Processing {source_file.name}")

            # 转换为YAML
            yaml_content = self.yaml_processor.json_to_yaml(json_data)

            # 为了生成schema和变量映射，我们需要使用受保护的数据
            protected_data, placeholder_map = self.yaml_processor.protect_jinja_syntax(json_data)

            # 生成schema（使用受保护的数据）
            schema = self.schema_generator.generate_schema(protected_data, placeholder_map)

            # 生成变量映射（使用受保护的数据）
            variable_mapping = self.variable_mapper.map_variables(protected_data, placeholder_map)

            # 创建输出文件路径
            relative_path = source_file.relative_to(source_file.parent.parent)
            yaml_file = output_dir / relative_path.with_suffix('.yaml')

            # 创建目录
            yaml_file.parent.mkdir(parents=True, exist_ok=True)

            # 直接写入纯YAML模板文件
            with open(yaml_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)

            # 创建元数据文件
            metadata_file = yaml_file.with_suffix('.meta.yaml')
            metadata = self._create_metadata(
                source_file.name,
                schema,
                variable_mapping,
                placeholder_map
            )

            with open(metadata_file, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True, indent=2)

            processing_time = time.time() - start_time

            # 收集统计信息
            statistics = {
                'jinja_variables': len(variable_mapping.variable_map),
                'regular_variables': len(variable_mapping.regular_variables),
                'special_variables': len(variable_mapping.special_variables),
                'schema_properties': len(schema.get('properties', {})),
                'yaml_lines': len(yaml_content.split('\n'))
            }

            # 警告信息
            warnings = []
            if len(variable_mapping.variable_map) > 10:
                warnings.append(f"Large number of variables ({len(variable_mapping.variable_map)})")

            if statistics['yaml_lines'] > 100:
                warnings.append(f"Large YAML file ({statistics['yaml_lines']} lines)")

            logger.info(f"Successfully converted {source_file.name} -> {yaml_file.name}")

            return ConversionResult(
                source_file=str(source_file),
                target_file=str(yaml_file),
                success=True,
                warnings=warnings,
                processing_time=processing_time,
                statistics=statistics
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to convert {source_file.name}: {e}")
            return ConversionResult(
                source_file=str(source_file),
                target_file="",
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )

    def _create_metadata(self, original_filename: str,
                       schema: Dict[str, Any],
                       variable_mapping: Any,
                       placeholder_map: Dict[str, Jinja2Placeholder]) -> Dict[str, Any]:
        """创建元数据"""

        # 解析协议ID
        protocol_id = self._extract_protocol_id(original_filename)
        family = protocol_id.split('-')[0] if '-' in protocol_id else 'unknown'

        metadata = {
            'protocol_id': protocol_id,
            'family': family,
            'original_filename': original_filename,
            'conversion_timestamp': datetime.now().isoformat(),
            'conversion_version': '1.0',
            'schema': schema,
            'variable_mapping': {
                'regular_variables': list(variable_mapping.regular_variables),
                'special_variables': list(variable_mapping.special_variables),
                'variable_paths': {name: info.yaml_paths for name, info in variable_mapping.variable_map.items()}
            },
            'jinja_placeholders': {
                placeholder_id: {
                    'original_content': info.original_content,
                    'type': info.type,
                    'location': info.location
                }
                for placeholder_id, info in placeholder_map.items()
            }
        }

        return metadata

    def _extract_protocol_id(self, filename: str) -> str:
        """从文件名提取协议ID"""
        # 移除扩展名
        name = Path(filename).stem
        return name

    def _update_stats(self, result: ConversionResult) -> None:
        """更新统计信息"""
        self.stats['total_processed'] += 1

        if result.success:
            self.stats['successful'] += 1
            self.stats['total_warnings'] += len(result.warnings)
            if result.statistics:
                self.stats['jinja_variables_found'] += result.statistics.get('jinja_variables', 0)
        else:
            self.stats['failed'] += 1

    def _generate_summary(self) -> Dict[str, Any]:
        """生成汇总信息"""
        return {
            'success_rate': (self.stats['successful'] / self.stats['total_processed'] * 100) if self.stats['total_processed'] > 0 else 0,
            'average_warnings_per_file': (self.stats['total_warnings'] / self.stats['successful']) if self.stats['successful'] > 0 else 0,
            'total_jinja_variables': self.stats['jinja_variables_found'],
            'processing_statistics': self.stats
        }

    def generate_report(self, report: MigrationReport, output_file: str = None) -> str:
        """生成详细的迁移报告"""
        lines = []
        lines.append("# Protocol Migration Report")
        lines.append("=" * 50)
        lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Processing time: {report.processing_time:.2f} seconds")
        lines.append("")

        # 总体统计
        lines.append("## Summary")
        lines.append(f"- Total files: {report.total_files}")
        lines.append(f"- Successful conversions: {report.successful_conversions}")
        lines.append(f"- Failed conversions: {report.failed_conversions}")
        lines.append(f"- Total warnings: {report.total_warnings}")
        lines.append(f"- Success rate: {report.successful_conversions/report.total_files*100:.1f}%")
        lines.append("")

        # 详细统计
        lines.append("## Statistics")
        for key, value in report.summary.items():
            if isinstance(value, dict):
                lines.append(f"### {key}")
                for sub_key, sub_value in value.items():
                    lines.append(f"- {sub_key}: {sub_value}")
            else:
                lines.append(f"- {key}: {value}")
        lines.append("")

        # 成功转换的文件
        if report.successful_conversions > 0:
            lines.append("## Successful Conversions")
            for result in report.results:
                if result.success:
                    lines.append(f"✅ {Path(result.source_file).name}")
                    if result.warnings:
                        for warning in result.warnings:
                            lines.append(f"   ⚠️  {warning}")
                    if result.statistics:
                        lines.append(f"   📊 Variables: {result.statistics.get('jinja_variables', 0)}, "
                                   f"Lines: {result.statistics.get('yaml_lines', 0)}")
            lines.append("")

        # 失败的文件
        if report.failed_conversions > 0:
            lines.append("## Failed Conversions")
            for result in report.results:
                if not result.success:
                    lines.append(f"❌ {Path(result.source_file).name}")
                    lines.append(f"   Error: {result.error_message}")
            lines.append("")

        report_content = "\n".join(lines)

        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Report saved to {output_file}")

        return report_content

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Migrate JSON protocol templates to YAML format")
    parser.add_argument("source_dir", help="Source directory containing JSON protocol files")
    parser.add_argument("-o", "--output", help="Output directory for YAML files", default="./protocols_yaml")
    parser.add_argument("-r", "--report", help="Output file for migration report", default="./migration_report.md")
    parser.add_argument("--backup", action="store_true", default=True, help="Create backup of existing files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        migrator = ProtocolMigrator(output_dir=args.output, backup=args.backup)
        report = migrator.migrate_directory(args.source_dir, args.output)

        # 生成报告
        report_content = migrator.generate_report(report, args.report)
        print(report_content)

        # 返回适当的退出码
        if report.failed_conversions > 0:
            logger.warning(f"Migration completed with {report.failed_conversions} failures")
            sys.exit(1)
        else:
            logger.info("Migration completed successfully")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()