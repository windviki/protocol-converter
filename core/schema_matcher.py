"""
基于Schema的智能匹配器
提供YAML schema验证和协议匹配功能
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import logging
from enum import Enum

from utils.yaml_schema import YamlSchemaGenerator, ValidationResult
from utils.yaml_path import YamlPath, PathError
from utils.variable_mapper import VariableMapper, VariableInfo, VariableMappingResult
from utils.yaml_processor import YamlProcessor, Jinja2Placeholder
# from models.types import ProtocolTemplate  # 假设存在这个类型

logger = logging.getLogger(__name__)

class MatchStrategy(Enum):
    """匹配策略"""
    STRICT = "strict"  # 严格匹配
    LENIENT = "lenient"  # 宽松匹配
    BEST_EFFORT = "best_effort"  # 尽力匹配

@dataclass
class MatchCandidate:
    """匹配候选"""
    template: Any  # ProtocolTemplate or similar
    score: float
    validation_result: ValidationResult
    variable_mapping: VariableMappingResult
    match_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MatchResult:
    """匹配结果"""
    protocol_template: Any
    validation_result: ValidationResult
    extracted_variables: Dict[str, Any]
    match_score: float
    variable_mapping: VariableMappingResult
    match_strategy: MatchStrategy
    processing_time: float = 0.0
    debug_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MatchConfiguration:
    """匹配配置"""
    strategy: MatchStrategy = MatchStrategy.BEST_EFFORT
    min_score_threshold: float = 0.3
    strict_mode: bool = False
    enable_path_validation: bool = True
    max_candidates: int = 50
    score_weights: Dict[str, float] = field(default_factory=lambda: {
        'validation': 0.6,
        'path_coverage': 0.3,
        'variable_completeness': 0.1
    })

class SchemaMatcher:
    """基于Schema的智能匹配器"""

    def __init__(self, config: MatchConfiguration = None):
        self.config = config or MatchConfiguration()
        self.schema_generator = YamlSchemaGenerator()
        self.variable_mapper = VariableMapper()
        self.yaml_processor = YamlProcessor()
        self.logger = logging.getLogger(__name__)

    def find_best_match(self, input_data: Any,
                       candidates: List[Any]) -> Optional[MatchResult]:
        """
        寻找最佳匹配

        Args:
            input_data: 输入数据
            candidates: 候选模板列表

        Returns:
            最佳匹配结果，如果没有匹配则返回None
        """
        import time
        start_time = time.time()

        if not candidates:
            self.logger.warning("No candidates provided for matching")
            return None

        self.logger.info(f"Starting match with {len(candidates)} candidates using {self.config.strategy.value} strategy")

        # 生成候选匹配列表
        match_candidates = []
        for i, template in enumerate(candidates[:self.config.max_candidates]):
            try:
                candidate = self._evaluate_candidate(input_data, template)
                if candidate and candidate.score >= self.config.min_score_threshold:
                    match_candidates.append(candidate)
            except Exception as e:
                self.logger.warning(f"Failed to evaluate candidate {i}: {e}")

        if not match_candidates:
            self.logger.warning("No candidates passed minimum score threshold")
            return None

        # 按分数排序
        match_candidates.sort(key=lambda x: x.score, reverse=True)

        # 选择最佳匹配
        best_candidate = match_candidates[0]
        processing_time = time.time() - start_time

        # 提取变量值
        extracted_vars = self._extract_variables(
            input_data,
            best_candidate.template,
            best_candidate.variable_mapping,
            best_candidate.validation_result.matched_paths
        )

        # 生成调试信息
        debug_info = {
            'total_candidates': len(candidates),
            'evaluated_candidates': len(match_candidates),
            'candidate_scores': [(c.template.protocol_id if hasattr(c.template, 'protocol_id') else f"template_{i}", c.score)
                                for i, c in enumerate(match_candidates[:5])],
            'strategy': self.config.strategy.value,
            'threshold_used': self.config.min_score_threshold
        }

        self.logger.info(f"Best match found: {best_candidate.template.protocol_id if hasattr(best_candidate.template, 'protocol_id') else 'unknown'} "
                        f"(score: {best_candidate.score:.3f}, time: {processing_time:.3f}s)")

        return MatchResult(
            protocol_template=best_candidate.template,
            validation_result=best_candidate.validation_result,
            extracted_variables=extracted_vars,
            match_score=best_candidate.score,
            variable_mapping=best_candidate.variable_mapping,
            match_strategy=self.config.strategy,
            processing_time=processing_time,
            debug_info=debug_info
        )

    def find_all_matches(self, input_data: Any,
                        candidates: List[Any]) -> List[MatchResult]:
        """
        寻找所有匹配

        Args:
            input_data: 输入数据
            candidates: 候选模板列表

        Returns:
            所有匹配结果列表（按分数降序排列）
        """
        import time
        start_time = time.time()

        self.logger.info(f"Finding all matches with {len(candidates)} candidates")

        match_results = []
        for template in candidates[:self.config.max_candidates]:
            try:
                candidate = self._evaluate_candidate(input_data, template)
                if candidate and candidate.score >= self.config.min_score_threshold:
                    # 提取变量值
                    extracted_vars = self._extract_variables(
                        input_data,
                        template,
                        candidate.variable_mapping,
                        candidate.validation_result.matched_paths
                    )

                    processing_time = time.time() - start_time
                    match_result = MatchResult(
                        protocol_template=template,
                        validation_result=candidate.validation_result,
                        extracted_variables=extracted_vars,
                        match_score=candidate.score,
                        variable_mapping=candidate.variable_mapping,
                        match_strategy=self.config.strategy,
                        processing_time=processing_time
                    )
                    match_results.append(match_result)

            except Exception as e:
                self.logger.warning(f"Failed to evaluate template: {e}")

        # 按分数排序
        match_results.sort(key=lambda x: x.match_score, reverse=True)

        self.logger.info(f"Found {len(match_results)} matches")
        return match_results

    def _evaluate_candidate(self, input_data: Any, template: Any) -> Optional[MatchCandidate]:
        """
        评估单个候选模板

        Args:
            input_data: 输入数据
            template: 模板对象

        Returns:
            匹配候选，如果无法匹配则返回None
        """
        try:
            # 获取模板的schema和变量映射
            schema = self._get_template_schema(template)
            variable_mapping = self._get_template_variable_mapping(template)

            # 使用schema验证
            validation_result = self.schema_generator.validate_data(
                input_data,
                schema,
                strict_mode=self.config.strict_mode
            )

            # 计算匹配分数
            score, match_details = self._calculate_match_score(
                validation_result,
                variable_mapping,
                input_data,
                template
            )

            if score > 0:
                return MatchCandidate(
                    template=template,
                    score=score,
                    validation_result=validation_result,
                    variable_mapping=variable_mapping,
                    match_details=match_details
                )

        except Exception as e:
            self.logger.warning(f"Failed to evaluate template {template}: {e}")

        return None

    def _get_template_schema(self, template: Any) -> Dict[str, Any]:
        """获取模板的schema"""
        if hasattr(template, 'schema'):
            return template.schema
        elif hasattr(template, 'yaml_schema'):
            return template.yaml_schema
        else:
            # 动态生成schema
            yaml_content = getattr(template, 'yaml_content', None) or getattr(template, 'template_content', None)
            if yaml_content:
                # 获取Jinja2占位符
                jinja_placeholders = getattr(template, 'jinja_placeholders', {})
                return self.schema_generator.generate_schema(yaml_content, jinja_placeholders)
            else:
                raise ValueError(f"Cannot generate schema for template {template}")

    def _get_template_variable_mapping(self, template: Any) -> VariableMappingResult:
        """获取模板的变量映射"""
        if hasattr(template, 'variable_mapping'):
            return template.variable_mapping
        else:
            # 动态生成变量映射
            yaml_content = getattr(template, 'yaml_content', None) or getattr(template, 'template_content', None)
            jinja_placeholders = getattr(template, 'jinja_placeholders', {})

            if yaml_content:
                return self.variable_mapper.map_variables(yaml_content, jinja_placeholders)
            else:
                raise ValueError(f"Cannot generate variable mapping for template {template}")

    def _calculate_match_score(self, validation_result: ValidationResult,
                             variable_mapping: VariableMappingResult,
                             input_data: Any,
                             template: Any) -> Tuple[float, Dict[str, Any]]:
        """
        计算匹配分数

        Returns:
            (分数, 详细信息)
        """
        weights = self.config.score_weights
        details = {}

        # 1. 验证分数
        if validation_result.is_valid:
            validation_score = 1.0
        else:
            # 根据错误数量计算分数
            error_penalty = min(len(validation_result.errors) * 0.2, 1.0)
            validation_score = max(0.0, 1.0 - error_penalty)

        details['validation_score'] = validation_score
        details['errors'] = len(validation_result.errors)
        details['warnings'] = len(validation_result.warnings)

        # 2. 路径覆盖度
        expected_paths = set()
        for var_info in variable_mapping.variable_map.values():
            expected_paths.update(var_info.yaml_paths)

        matched_paths = set(validation_result.matched_paths)
        if expected_paths:
            path_coverage = len(matched_paths & expected_paths) / len(expected_paths)
        else:
            path_coverage = 1.0  # 如果没有期望路径，认为完全覆盖

        details['path_coverage'] = path_coverage
        details['expected_paths'] = len(expected_paths)
        details['matched_paths'] = len(matched_paths)

        # 3. 变量完整性
        total_vars = len(variable_mapping.variable_map)
        if total_vars > 0:
            vars_with_values = 0
            for var_name in variable_mapping.variable_map:
                if self._can_extract_variable_value(var_name, input_data, variable_mapping):
                    vars_with_values += 1
            variable_completeness = vars_with_values / total_vars
        else:
            variable_completeness = 1.0

        details['variable_completeness'] = variable_completeness
        details['total_variables'] = total_vars

        # 4. 根据策略调整分数
        if self.config.strategy == MatchStrategy.STRICT:
            # 严格模式：验证失败则分数为0
            if not validation_result.is_valid:
                final_score = 0.0
            else:
                final_score = (validation_score * weights['validation'] +
                             path_coverage * weights['path_coverage'] +
                             variable_completeness * weights['variable_completeness'])

        elif self.config.strategy == MatchStrategy.LENIENT:
            # 宽松模式：更注重路径覆盖
            final_score = (validation_score * 0.3 +
                         path_coverage * 0.5 +
                         variable_completeness * 0.2)

        else:  # BEST_EFFORT
            # 尽力模式：综合考虑所有因素
            final_score = (validation_score * weights['validation'] +
                         path_coverage * weights['path_coverage'] +
                         variable_completeness * weights['variable_completeness'])

        # 确保分数在有效范围内
        final_score = max(0.0, min(1.0, final_score))
        details['final_score'] = final_score

        return final_score, details

    def _can_extract_variable_value(self, var_name: str, input_data: Any,
                                  variable_mapping: VariableMappingResult) -> bool:
        """检查是否能够提取变量的值"""
        var_info = variable_mapping.variable_map.get(var_name)
        if not var_info:
            return False

        # 尝试从每个可能的路径提取值
        for path_str in var_info.yaml_paths:
            try:
                yaml_path = YamlPath(path_str)
                value = yaml_path.get_value(input_data)
                if value is not None:
                    return True
            except PathError:
                continue

        return False

    def _extract_variables(self, input_data: Any, template: Any,
                          variable_mapping: VariableMappingResult,
                          matched_paths: List[str]) -> Dict[str, Any]:
        """
        提取变量值

        Args:
            input_data: 输入数据
            template: 模板
            variable_mapping: 变量映射
            matched_paths: 匹配的路径

        Returns:
            提取的变量值字典
        """
        extracted_vars = {}

        for var_name, var_info in variable_mapping.variable_map.items():
            try:
                # 尝试从每个可能的路径提取值
                value = None
                used_path = None

                for path_str in var_info.yaml_paths:
                    try:
                        yaml_path = YamlPath(path_str)
                        value = yaml_path.get_value(input_data)
                        if value is not None:
                            used_path = path_str
                            break
                    except PathError:
                        continue

                # 如果找到值，应用过滤器
                if value is not None:
                    processed_value = self._apply_filters(value, var_info.filters)
                    extracted_vars[var_name] = processed_value

                    self.logger.debug(f"Extracted variable '{var_name}' = {processed_value} from path '{used_path}'")

                # 应用默认值
                elif var_info.default_value is not None:
                    extracted_vars[var_name] = var_info.default_value
                    self.logger.debug(f"Using default value for variable '{var_name}' = {var_info.default_value}")

                # 特殊变量处理
                elif var_info.variable_type == 'special':
                    # 特殊变量可能需要特殊处理
                    special_value = self._handle_special_variable(var_name, input_data, template)
                    if special_value is not None:
                        extracted_vars[var_name] = special_value

            except Exception as e:
                self.logger.warning(f"Failed to extract variable '{var_name}': {e}")

        return extracted_vars

    def _apply_filters(self, value: Any, filters: List[str]) -> Any:
        """应用变量过滤器"""
        result = value

        for filter_name in filters:
            try:
                if filter_name == 'upper':
                    result = str(result).upper()
                elif filter_name == 'lower':
                    result = str(result).lower()
                elif filter_name == 'capitalize':
                    result = str(result).capitalize()
                elif filter_name == 'title':
                    result = str(result).title()
                elif filter_name == 'default':
                    # default过滤器已经在变量映射阶段处理
                    continue
                # 可以添加更多过滤器
            except Exception as e:
                self.logger.warning(f"Failed to apply filter '{filter_name}': {e}")

        return result

    def _handle_special_variable(self, var_name: str, input_data: Any, template: Any) -> Any:
        """处理特殊变量"""
        # 这里可以实现特殊变量的逻辑
        # 例如 __session_id, __array_index 等

        if var_name == '__session_id':
            # 生成会话ID
            import uuid
            return str(uuid.uuid4())[:8]

        elif var_name == '__array_index':
            # 数组索引需要上下文信息
            return 0  # 默认值

        elif var_name == '__array_total':
            # 数组总数需要上下文信息
            return 1  # 默认值

        # 其他特殊变量...
        return None

    def get_match_report(self, match_result: MatchResult) -> str:
        """生成详细的匹配报告"""
        lines = []
        lines.append("Protocol Match Report")
        lines.append("=" * 40)

        # 基本信息
        template_id = getattr(match_result.protocol_template, 'protocol_id', 'unknown')
        lines.append(f"Template ID: {template_id}")
        lines.append(f"Match Score: {match_result.match_score:.3f}")
        lines.append(f"Strategy: {match_result.match_strategy.value}")
        lines.append(f"Processing Time: {match_result.processing_time:.3f}s")
        lines.append(f"Validation: {match_result.validation_result.get_summary()}")

        # 验证详情
        if match_result.validation_result.errors:
            lines.append("\n❌ Validation Errors:")
            for error in match_result.validation_result.errors[:10]:
                lines.append(f"  - {error}")
            if len(match_result.validation_result.errors) > 10:
                lines.append(f"  ... and {len(match_result.validation_result.errors) - 10} more errors")

        if match_result.validation_result.warnings:
            lines.append("\n⚠️  Validation Warnings:")
            for warning in match_result.validation_result.warnings[:5]:
                lines.append(f"  - {warning}")
            if len(match_result.validation_result.warnings) > 5:
                lines.append(f"  ... and {len(match_result.validation_result.warnings) - 5} more warnings")

        # 变量提取结果
        lines.append(f"\n📊 Extracted Variables ({len(match_result.extracted_variables)}):")
        for var_name, value in sorted(match_result.extracted_variables.items()):
            var_info = match_result.variable_mapping.variable_map.get(var_name)
            var_type = var_info.variable_type if var_info else 'unknown'
            type_icon = '🔧' if var_type == 'special' else '📝'
            lines.append(f"  {type_icon} {var_name}: {value} ({var_type})")

        # 未提取的变量
        missing_vars = set(match_result.variable_mapping.variable_map.keys()) - set(match_result.extracted_variables.keys())
        if missing_vars:
            lines.append(f"\n❓ Missing Variables ({len(missing_vars)}):")
            for var_name in sorted(missing_vars):
                var_info = match_result.variable_mapping.variable_map[var_name]
                lines.append(f"  - {var_name} (type: {var_info.variable_type})")
                if var_info.default_value:
                    lines.append(f"    default: {var_info.default_value}")

        # 路径覆盖信息
        lines.append(f"\n🛤️  Path Coverage:")
        lines.append(f"  Matched paths: {len(match_result.validation_result.matched_paths)}")
        lines.append(f"  Unmatched paths: {len(match_result.validation_result.unmatched_paths)}")

        # 调试信息
        if match_result.debug_info:
            lines.append(f"\n🐛 Debug Info:")
            for key, value in match_result.debug_info.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def update_config(self, **kwargs) -> None:
        """更新匹配配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                self.logger.warning(f"Unknown config key: {key}")

# 便利函数
def match_protocol(input_data: Any, templates: List[Any],
                  strategy: str = "best_effort",
                  min_score: float = 0.3) -> Optional[MatchResult]:
    """匹配协议的便利函数"""
    config = MatchConfiguration(
        strategy=MatchStrategy(strategy),
        min_score_threshold=min_score
    )
    matcher = SchemaMatcher(config)
    return matcher.find_best_match(input_data, templates)