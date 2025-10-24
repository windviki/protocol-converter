"""
Field Mapper - 处理协议间的字段映射转换
支持复杂的多字段到单字段、单字段到多字段的映射
"""

import re
import yaml
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FieldMapper:
    """字段映射器"""

    def __init__(self, mapping_config_path: str = None):
        """初始化字段映射器"""
        self.mapping_config = {}
        self.processors = {}

        if mapping_config_path:
            self.load_mappings(mapping_config_path)
        else:
            self.load_default_mappings()

    def load_mappings(self, config_path: str):
        """加载映射配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.mapping_config = config.get('mappings', {})
            processor_configs = config.get('processors', {})
            self.defaults = config.get('defaults', {})

            # 注册处理器
            for name, proc_config in processor_configs.items():
                self.register_processor(name, proc_config)

            logger.info(f"Loaded field mappings from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load mapping config: {e}")
            self.load_default_mappings()

    def load_default_mappings(self):
        """加载默认映射配置"""
        # 默认的处理器实现
        self.processors = {
            'split_intersection': self.split_intersection,
            'combine_intersection': self.combine_intersection,
            'direct_mapping': lambda x: x
        }

        # 默认的映射规则
        self.mapping_config = {
            'A-4 <-> B-4': {
                'destination_to_intersection': {
                    'from': 'destination',
                    'to': ['intersection.primary_road', 'intersection.secondary_road'],
                    'processor': 'split_intersection'
                },
                'intersection_to_destination': {
                    'from': ['intersection.primary_road', 'intersection.secondary_road'],
                    'to': 'destination',
                    'processor': 'combine_intersection'
                }
            }
        }

        self.defaults = {
            'B-4': {
                'city': '上海',
                'district': '长宁区',
                'vehicle_type': 'car',
                'avoid_tolls': False,
                'urgency': 'normal'
            }
        }

        logger.info("Loaded default field mappings")

    def register_processor(self, name: str, config: Dict[str, Any]):
        """注册处理器"""
        implementation = config.get('implementation', '')
        if implementation:
            # 简化实现：直接使用预定义的处理器
            if name == 'split_intersection':
                self.processors[name] = self.split_intersection
            elif name == 'combine_intersection':
                self.processors[name] = self.combine_intersection
            elif name == 'direct_mapping':
                self.processors[name] = lambda x: x
            else:
                logger.warning(f"Unknown processor: {name}")

    def process_mapping(self, mapping_vars: Dict[str, Any],
                       source_protocol: str, target_protocol: str,
                       source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理字段映射

        Args:
            mapping_vars: 需要映射的变量
            source_protocol: 源协议ID
            target_protocol: 目标协议ID
            source_data: 源数据

        Returns:
            映射后的变量字典
        """
        mapped_vars = {}

        # 确定映射键
        mapping_key = f"{source_protocol} <-> {target_protocol}"
        reverse_key = f"{target_protocol} <-> {source_protocol}"

        # 选择正确的映射配置
        if mapping_key in self.mapping_config:
            mapping_rules = self.mapping_config[mapping_key]
        elif reverse_key in self.mapping_config:
            mapping_rules = self.mapping_config[reverse_key]
        else:
            logger.warning(f"No mapping found for {source_protocol} <-> {target_protocol}")
            return mapping_vars

        logger.debug(f"Processing mapping: {source_protocol} -> {target_protocol}")
        logger.debug(f"Mapping vars: {mapping_vars}")
        logger.debug(f"Mapping rules type: {type(mapping_rules)}")
        logger.debug(f"Mapping rules: {mapping_rules}")

        # 处理每个映射规则
        for rule_name, rule_config in mapping_rules.items():
            try:
                logger.debug(f"Processing rule {rule_name}: {rule_config}")
                # 获取源字段模式
                source_pattern = rule_config.get('from')
                if not source_pattern:
                    logger.warning(f"No 'from' field in mapping rule {rule_name}")
                    continue

                logger.debug(f"Source pattern: {source_pattern} (type: {type(source_pattern)})")
                result = self._process_single_mapping(
                    source_pattern, rule_config, mapping_vars, source_data
                )
                logger.debug(f"Rule {rule_name} result: {result}")
                if result:
                    mapped_vars.update(result)
            except Exception as e:
                logger.error(f"Error processing mapping {rule_name}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

        # 添加默认值
        if target_protocol in self.defaults:
            for key, value in self.defaults[target_protocol].items():
                if key not in mapped_vars and key not in mapping_vars:
                    mapped_vars[key] = value

        logger.debug(f"Mapped vars result: {mapped_vars}")
        return mapped_vars

    def _process_single_mapping(self, source_pattern: Any, rule: Dict[str, Any],
                              mapping_vars: Dict[str, Any], source_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个映射规则"""
        processor_name = rule.get('processor', 'direct_mapping')
        processor = self.processors.get(processor_name)

        if not processor:
            logger.warning(f"Unknown processor: {processor_name}")
            return {}

        # 提取源数据
        if isinstance(source_pattern, list):
            # 多源字段到单目标字段
            source_values = []
            for field_path in source_pattern:
                value = self._extract_field_value(field_path, mapping_vars, source_data)
                source_values.append(value)

            result_value = processor(*source_values)
            target_path = rule.get('to')

            if isinstance(target_path, str):
                return {target_path: result_value}
            elif isinstance(target_path, list):
                return dict(zip(target_path, result_value) if isinstance(result_value, list) else {target_path[0]: result_value})

        elif isinstance(source_pattern, str):
            # 单源字段到目标字段
            source_value = self._extract_field_value(source_pattern, mapping_vars, source_data)
            result_value = processor(source_value)

            target_path = rule.get('to')
            if target_path:
                if isinstance(target_path, str):
                    return {target_path: result_value}
                elif isinstance(target_path, list):
                    # 如果目标路径是列表，且结果也是列表，进行一对一映射
                    if isinstance(result_value, list):
                        return dict(zip(target_path, result_value))
                    else:
                        # 如果结果是单一值，但目标路径是列表，映射到所有目标
                        return {path: result_value for path in target_path}

        return {}

    def _extract_field_value(self, field_path: str, mapping_vars: Dict[str, Any],
                           source_data: Dict[str, Any]) -> Any:
        """从数据中提取字段值"""
        # 首先从mapping_vars中查找
        if field_path in mapping_vars:
            return mapping_vars[field_path]

        # 然后从source_data中查找
        value = self._get_nested_value(source_data, field_path.split('.'))
        if value is not None:
            return value

        # 最后返回None
        logger.debug(f"Field {field_path} not found, returning None")
        return None

    def _get_nested_value(self, data: Dict[str, Any], path_parts: List[str]) -> Any:
        """获取嵌套字典中的值"""
        current = data
        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    # 处理器实现
    def split_intersection(self, value: str) -> List[str]:
        """分割交叉口字符串为主路和次路"""
        if not isinstance(value, str):
            return [str(value), '']

        # 尝试多种分割模式
        patterns = [
            r'与|和|及',
            r'[\-\-]',
            r'\s+和\s+',
            r'\s+与\s+',
        ]

        for pattern in patterns:
            parts = re.split(pattern, value)
            if len(parts) >= 2:
                return [parts[0].strip(), parts[1].strip()]

        return [value, '']

    def combine_intersection(self, primary: str, secondary: str = '') -> str:
        """将主路和次路合并为交叉口字符串"""
        if primary and secondary:
            return f"{primary}与{secondary}"
        elif primary:
            return primary
        elif secondary:
            return secondary
        else:
            return ''

def create_field_mapper(mapping_config_path: str = None) -> FieldMapper:
    """创建字段映射器实例"""
    if not mapping_config_path:
        # 使用默认路径
        default_path = Path(__file__).parent.parent / "protocols" / "field_mappings.yaml"
        if default_path.exists():
            mapping_config_path = str(default_path)

    return FieldMapper(mapping_config_path)