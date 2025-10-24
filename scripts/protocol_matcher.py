#!/usr/bin/env python3
"""
协议匹配验证工具
用于验证输入JSON与哪个YAML协议模板匹配
"""

import json
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.yaml_processor import YamlProcessor
from utils.yaml_schema import YamlSchemaGenerator
from utils.variable_mapper import VariableMapper
from core.schema_matcher import SchemaMatcher, MatchResult, MatchConfiguration

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MatchScore:
    """匹配分数"""
    protocol_id: str
    family: str
    match_score: float
    validation_errors: int
    validation_warnings: int
    variables_extracted: int
    variables_total: int
    path_coverage: float

class ProtocolMatcher:
    """协议匹配验证器"""

    def __init__(self, yaml_dir: str, strict_mode: bool = False):
        self.yaml_dir = Path(yaml_dir)
        self.strict_mode = strict_mode
        self.yaml_processor = YamlProcessor()
        self.schema_generator = YamlSchemaGenerator()
        self.variable_mapper = VariableMapper()
        self.matcher = SchemaMatcher(MatchConfiguration(strict_mode=strict_mode))

        # 加载所有协议模板
        self.templates = self._load_templates()

    def _load_templates(self) -> List[Dict[str, Any]]:
        """加载所有YAML协议模板"""
        templates = []

        for yaml_file in self.yaml_dir.rglob("*.yaml"):
            if not yaml_file.name.endswith('.meta.yaml'):  # 跳过元数据文件
                try:
                    template = self._load_template(yaml_file)
                    if template:
                        templates.append(template)
                        logger.info(f"Loaded template: {yaml_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to load template {yaml_file.name}: {e}")

        return templates

    def _load_template(self, yaml_file: Path) -> Optional[Dict[str, Any]]:
        """加载单个协议模板"""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml_content = f.read()

            # 检查是否是纯模板文件（没有metadata字段）
            if 'metadata:' not in yaml_content:
                # 纯YAML模板文件
                # 使用YamlProcessor的方法安全地转换YAML内容
                try:
                    temp_json_data = self.yaml_processor.yaml_to_json(yaml_content)
                except Exception as e:
                    logger.error(f"Failed to convert YAML to JSON for {yaml_file.name}: {e}")
                    return None

                # 保护Jinja2语法并生成schema和变量映射
                protected_data, placeholder_map = self.yaml_processor.protect_jinja_syntax(temp_json_data)

                # 从文件名提取协议族
                protocol_id = yaml_file.stem
                family = protocol_id.split('-')[0] if '-' in protocol_id else 'unknown'

                return {
                    'file_path': str(yaml_file),
                    'protocol_id': protocol_id,
                    'family': family,
                    'yaml_content': yaml_content,
                    'template_data': temp_json_data,
                    'schema': self.schema_generator.generate_schema(protected_data, placeholder_map),
                    'variable_mapping': self.variable_mapper.map_variables(protected_data, placeholder_map),
                    'jinja_placeholders': placeholder_map,
                    'type': 'pure_template'
                }

            else:
                # 完整的YAML文件（包含metadata）
                return None

        except Exception as e:
            logger.error(f"Error loading template {yaml_file}: {e}")
            return None

    def find_matches(self, input_json: Dict[str, Any],
                    min_score: float = 0.1,
                    max_results: int = 10) -> List[MatchScore]:
        """
        查找匹配的协议模板

        Args:
            input_json: 输入JSON数据
            min_score: 最低匹配分数
            max_results: 返回的最大结果数

        Returns:
            按匹配分数排序的匹配结果列表
        """
        logger.info(f"Finding matches for input data with min_score={min_score}")

        matches = []

        for template in self.templates:
            try:
                # 使用schema匹配器验证
                match_result = self.matcher.find_best_match(input_json, [template])

                if match_result and match_result.match_score >= min_score:
                    score = MatchScore(
                        protocol_id=template['protocol_id'],
                        family=template.get('family', 'unknown'),
                        match_score=match_result.match_score,
                        validation_errors=len([e for e in match_result.validation_result.errors if e.severity == 'error']),
                        validation_warnings=len([w for w in match_result.validation_result.warnings if w.severity == 'warning']),
                        variables_extracted=len(match_result.extracted_variables),
                        variables_total=len(match_result.variable_mapping.variable_map),
                        path_coverage=len(match_result.validation_result.matched_paths) / max(len(match_result.validation_result.unmatched_paths), 1)
                    )
                    matches.append(score)
                    logger.debug(f"Match found: {template['protocol_id']} -> score={match_result.match_score:.3f}")

            except Exception as e:
                logger.warning(f"Failed to match with template {template['protocol_id']}: {e}")

        # 按分数排序
        matches.sort(key=lambda x: x.match_score, reverse=True)

        return matches[:max_results]

    def format_match_results(self, matches: List[MatchScore], detailed: bool = False) -> str:
        """格式化匹配结果"""
        lines = []
        lines.append("Protocol Match Results")
        lines.append("=" * 50)
        lines.append(f"Searched {len(self.templates)} protocol templates")
        lines.append(f"Found {len(matches)} matches above threshold")
        lines.append("")

        if detailed:
            lines.append("## Detailed Results")
            for i, match in enumerate(matches, 1):
                lines.append(f"### {i}. {match.protocol_id} (Family: {match.family})")
                lines.append(f"   **Match Score**: {match.match_score:.3f}")
                lines.append(f"   **Validation**: {match.validation_errors} errors, {match.validation_warnings} warnings")
                lines.append(f"   **Variables**: {match.variables_extracted}/{match.variables_total} extracted")
                lines.append(f"   **Path Coverage**: {match.path_coverage:.1%}")

                if match.validation_errors > 0 or match.validation_warnings > 0:
                    lines.append("   **Validation Issues**:")
                    if match.validation_errors > 0:
                        lines.append(f"     ❌ {match.validation_errors} validation errors")
                    if match.validation_warnings > 0:
                        lines.append(f"     ⚠️ {match.validation_warnings} warnings")

                lines.append("")
        else:
            lines.append("## Top Matches")
            for i, match in enumerate(matches[:5], 1):  # 只显示前5个
                lines.append(f"{i}. {match.protocol_id} - Score: {match.match_score:.3f} ({match.variables_extracted}/{match.variables_total} vars)")

        return "\n".join(lines)

    def convert_and_match(self, json_input: Any,
                        json_file: str = None,
                        min_score: float = 0.1,
                        max_results: int = 10) -> List[MatchScore]:
        """
        转换JSON输入并查找匹配

        Args:
            json_input: JSON输入（文件路径或数据）
            json_file: JSON文件路径（如果为None，则json_input应为数据）
            min_score: 最低匹配分数
            max_results: 最大结果数

        Returns:
            匹配结果列表
        """
        # 读取输入数据
        if json_file:
            with open(json_file, 'r', encoding='utf-8') as f:
                input_json = json.load(f)
        elif isinstance(json_input, str):
            input_json = json.loads(json_input)
        elif isinstance(json_input, dict):
            input_json = json_input
        else:
            raise ValueError("Invalid JSON input")

        logger.info(f"Processing input data with {len(input_json)} fields")

        # 查找匹配
        return self.find_matches(input_json, min_score, max_results)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Find matching protocol templates for input JSON data")

    parser.add_argument("input", help="Input JSON data (file path or JSON string)")
    parser.add_argument("--yaml-dir", "-y", default="./protocols_yaml",
                       help="Directory containing YAML protocol templates")
    parser.add_argument("--json-file", "-f",
                       help="Read input from JSON file instead of argument")
    parser.add_argument("--min-score", "-m", type=float, default=0.1,
                       help="Minimum match score threshold (default: 0.1)")
    parser.add_argument("--max-results", "-n", type=int, default=10,
                       help="Maximum number of results to return (default: 10)")
    parser.add_argument("--detailed", "-d", action="store_true",
                       help="Show detailed match information")
    parser.add_argument("--strict", action="store_true",
                       help="Use strict validation mode")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # 初始化匹配器
        matcher = ProtocolMatcher(args.yaml_dir, args.strict)

        # 转换和匹配
        results = matcher.convert_and_match(
            json_input=args.input,
            json_file=args.json_file,
            min_score=args.min_score,
            max_results=args.max_results
        )

        # 输出结果
        output = matcher.format_match_results(results, detailed=args.detailed)
        print(output)

        if len(results) == 0:
            logger.warning("No matching protocols found")
            sys.exit(1)
        else:
            logger.info(f"Found {len(results)} matching protocols")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()