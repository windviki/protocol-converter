#!/usr/bin/env python3
"""
简化的协议匹配工具
使用结构化匹配快速找到匹配的协议模板
"""

import json
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import yaml

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SimpleMatch:
    """简单匹配结果"""
    protocol_id: str
    family: str
    match_score: float
    matched_fields: List[str]
    missing_fields: List[str]
    structure_match: bool
    confidence: str  # 'high', 'medium', 'low'

class SimpleProtocolMatcher:
    """简化的协议匹配器"""

    def __init__(self, yaml_dir: str):
        self.yaml_dir = Path(yaml_dir)
        self.templates = self._load_templates()

    def _load_templates(self) -> List[Dict[str, Any]]:
        """加载所有YAML协议模板"""
        templates = []
        template_count = 0

        for yaml_file in self.yaml_dir.rglob("*.yaml"):
            if yaml_file.name.endswith('.meta.yaml'):  # 跳过元数据文件
                continue

            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    yaml_content = f.read()

                # 检查是否是纯模板文件
                if 'metadata:' not in yaml_content:
                    # 提取基本结构信息
                    template_info = self._extract_structure_info(yaml_content, yaml_file.name)
                    if template_info:
                        templates.append(template_info)
                        template_count += 1

            except Exception as e:
                logger.warning(f"Failed to load template {yaml_file.name}: {e}")

        logger.info(f"Loaded {template_count} YAML protocol templates")
        return templates

    def _extract_structure_info(self, yaml_content: str, filename: str) -> Optional[Dict[str, Any]]:
        """提取YAML模板的结构信息"""
        try:
            # 移除Jinja2语法，提取纯结构
            cleaned_yaml = self._remove_jinja_syntax(yaml_content)

            # 解析结构
            structure = yaml.safe_load(cleaned_yaml)

            # 提取Jinja2变量
            jinja_vars = self._extract_jinja_variables(yaml_content)

            # 提取协议信息
            protocol_id = Path(filename).stem
            family = protocol_id.split('-')[0] if '-' in protocol_id else 'unknown'

            return {
                'protocol_id': protocol_id,
                'family': family,
                'filename': filename,
                'raw_content': yaml_content,
                'structure': structure,
                'jinja_variables': jinja_vars,
                'field_paths': self._extract_field_paths(structure)
            }

        except Exception as e:
            logger.warning(f"Failed to extract structure from {filename}: {e}")
            return None

    def _remove_jinja_syntax(self, yaml_content: str) -> str:
        """移除Jinja2语法，保留纯结构"""
        result = yaml_content

        # 移除变量 {{ var }}
        import re
        result = re.sub(r'\{\{\s*[^}]+\s*\}\}', '__JINJA_VAR__', result)

        # 移除语句 {% stmt %}
        result = re.sub(r'\{\%\s*[^%]+\s*\%\}', '__JINJA_STMT__', result)

        # 移除注释 {# comment #}
        result = re.sub(r'\{\#\s*[^#]+\s*\#\}', '# Jinja comment', result)

        return result

    def _extract_jinja_variables(self, yaml_content: str) -> List[str]:
        """提取所有Jinja2变量名"""
        variables = []

        # 提取变量 {{ var }}
        import re
        var_matches = re.findall(r'\{\{\s*([^|}]+?)(?:\s*\|[^}]*)?\s*\}\}', yaml_content)
        for var in var_matches:
            var_name = var.strip()
            if var_name and var_name not in variables:
                variables.append(var_name)

        return variables

    def _extract_field_paths(self, structure: Any, prefix: str = "") -> List[str]:
        """提取所有字段的路径"""
        paths = []

        if isinstance(structure, dict):
            for key, value in structure.items():
                current_path = f"{prefix}.{key}" if prefix else key
                paths.append(current_path)
                paths.extend(self._extract_field_paths(value, current_path))

        elif isinstance(structure, list):
            for i, item in enumerate(structure):
                current_path = f"{prefix}[{i}]" if prefix else f"[{i}]"
                paths.extend(self._extract_field_paths(item, current_path))

        return paths

    def calculate_match_score(self, input_data: Dict[str, Any], template: Dict[str, Any]) -> SimpleMatch:
        """计算匹配分数"""
        input_paths = self._extract_field_paths(input_data)
        template_paths = template['field_paths']

        # 计算路径匹配度
        common_paths = set(input_paths) & set(template_paths)
        path_coverage = len(common_paths) / len(template_paths) if template_paths else 0

        # 计算结构匹配度
        structure_match = self._compare_structure(input_data, template['structure'])

        # 提取缺失和匹配的字段
        matched_fields = list(common_paths)
        missing_fields = list(set(template_paths) - set(input_paths))

        # 计算综合分数
        base_score = 0.0
        if structure_match:
            base_score = 0.7  # 结构匹配基础分

        score = base_score + (path_coverage * 0.3)

        # 确定置信度
        confidence = 'low'
        if score >= 0.8:
            confidence = 'high'
        elif score >= 0.6:
            confidence = 'medium'
        elif score >= 0.4:
            confidence = 'low'
        else:
            confidence = 'very_low'

        return SimpleMatch(
            protocol_id=template['protocol_id'],
            family=template['family'],
            match_score=score,
            matched_fields=matched_fields,
            missing_fields=missing_fields,
            structure_match=structure_match,
            confidence=confidence
        )

    def _compare_structure(self, data1: Any, data2: Any) -> bool:
        """比较两个数据结构的相似性"""
        if type(data1) != type(data2):
            return False

        if isinstance(data1, dict):
            if len(data1) != len(data2):
                return False
            return all(self._compare_structure(data1[key], data2.get(key)) for key in data1.keys())

        elif isinstance(data1, list):
            if len(data1) != len(data2):
                return False
            return all(self._compare_structure(data1[i], data2[i]) for i in range(len(data1)))

        else:
            return True

    def find_matches(self, input_data: Dict[str, Any],
                    min_score: float = 0.1,
                    max_results: int = 5) -> List[SimpleMatch]:
        """查找匹配的协议模板"""
        matches = []

        for template in self.templates:
            try:
                match = self.calculate_match_score(input_data, template)
                if match.match_score >= min_score:
                    matches.append(match)
            except Exception as e:
                logger.warning(f"Failed to calculate match for {template['protocol_id']}: {e}")

        # 按分数排序
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches[:max_results]

    def format_results(self, matches: List[SimpleMatch], detailed: bool = False) -> str:
        """格式化匹配结果"""
        lines = []
        lines.append("Protocol Match Results")
        lines.append("=" * 50)
        lines.append(f"Found {len(matches)} matching protocols")
        lines.append("")

        if detailed:
            for i, match in enumerate(matches, 1):
                lines.append(f"### {i}. {match.protocol_id} (Family: {match.family})")
                lines.append(f"   **Match Score**: {match.match_score:.3f}")
                lines.append(f"   **Confidence**: {match.confidence}")
                lines.append(f"   **Structure Match**: {'✓' if match.structure_match else '✗'}")
                lines.append(f"   **Matched Fields**: {len(match.matched_fields)}")
                lines.append(f"   **Missing Fields**: {len(match.missing_fields)}")

                if match.matched_fields:
                    lines.append("   **Matched Field Paths**:")
                    for field in match.matched_fields[:5]:  # 只显示前5个
                        lines.append(f"     ✓ {field}")
                    if len(match.matched_fields) > 5:
                        lines.append(f"     ... and {len(match.matched_fields) - 5} more")

                if match.missing_fields and len(match.missing_fields) <= 5:
                    lines.append("   **Missing Field Paths**:")
                    for field in match.missing_fields:
                        lines.append(f"     ✗ {field}")

                lines.append("")
        else:
            lines.append("## Top Matches")
            for i, match in enumerate(matches[:5], 1):
                status = "✓" if match.structure_match else "✗"
                lines.append(f"{i}. {match.protocol_id} - Score: {match.match_score:.3f} ({match.confidence}) {status}")

        return "\n".join(lines)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Find matching protocol templates using structural matching")
    parser.add_argument("input", help="Input JSON file path")
    parser.add_argument("--yaml-dir", "-y", default="./protocols_yaml",
                       help="Directory containing YAML protocol templates")
    parser.add_argument("--min-score", "-m", type=float, default=0.1,
                       help="Minimum match score threshold (default: 0.1)")
    parser.add_argument("--max-results", "-n", type=int, default=5,
                       help="Maximum number of results to return (default: 5)")
    parser.add_argument("--detailed", "-d", action="store_true",
                       help="Show detailed match information")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # 初始化匹配器
        matcher = SimpleProtocolMatcher(args.yaml_dir)

        # 读取输入数据
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)

        logger.info(f"Processing input data with {len(input_data)} top-level fields")

        # 查找匹配
        matches = matcher.find_matches(
            input_data,
            min_score=args.min_score,
            max_results=args.max_results
        )

        # 输出结果
        output = matcher.format_results(matches, detailed=args.detailed)
        print(output)

        if len(matches) == 0:
            logger.warning("No matching protocols found")
            sys.exit(1)
        else:
            logger.info(f"Found {len(matches)} matching protocols")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()