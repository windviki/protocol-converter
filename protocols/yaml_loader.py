"""
YAML协议加载器
支持加载YAML格式的协议模板，提供更强大的功能
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
import yaml

from utils.yaml_processor import YamlProcessor, Jinja2Placeholder
from utils.yaml_schema import YamlSchemaGenerator, ValidationResult
from utils.variable_mapper import VariableMapper, VariableMappingResult
from core.converter import ProtocolConverter
from models.types import ProtocolTemplate, ArrayMarker
from database.manager import ProtocolDatabase

logger = logging.getLogger(__name__)

@dataclass
class YamlProtocolTemplate:
    """YAML协议模板数据结构"""
    protocol_id: str
    family: str
    file_path: str
    yaml_content: str
    template_data: Dict[str, Any]
    schema: Dict[str, Any]
    variable_mapping: VariableMappingResult
    jinja_placeholders: Dict[str, Jinja2Placeholder]
    validation_result: Optional[ValidationResult] = None
    metadata: Dict[str, Any] = None

class YamlProtocolLoader:
    """YAML协议加载器"""

    def __init__(self, db_path: str = "protocols.db", yaml_dir: str = "./protocols_yaml"):
        self.db = ProtocolDatabase(db_path)
        self.converter = ProtocolConverter()
        self.yaml_dir = Path(yaml_dir)

        # YAML处理工具
        self.yaml_processor = YamlProcessor()
        self.schema_generator = YamlSchemaGenerator()
        self.variable_mapper = VariableMapper()

        # 加载状态
        self.loaded_templates: Dict[str, YamlProtocolTemplate] = {}

        logger.info(f"YAML Protocol Loader initialized with yaml_dir: {yaml_dir}")

    def load_from_directory(self, directory: str = None) -> int:
        """
        从目录加载所有YAML协议文件

        Args:
            directory: 协议文件目录，如果为None则使用默认的yaml_dir

        Returns:
            加载的协议数量
        """
        if directory is None:
            directory = str(self.yaml_dir)

        if not os.path.exists(directory):
            logger.error(f"Directory not found: {directory}")
            return 0

        loaded_count = 0
        yaml_files = self._find_yaml_files(directory)

        logger.info(f"Found {len(yaml_files)} YAML files to process")

        for file_path in yaml_files:
            try:
                template = self._load_yaml_file(file_path)
                if template:
                    self.loaded_templates[template.protocol_id] = template
                    self._save_to_database(template)
                    self._load_to_converter(template)
                    loaded_count += 1
                    logger.info(f"Loaded YAML protocol: {template.protocol_id}")
            except Exception as e:
                logger.error(f"Error loading YAML file {file_path}: {e}")

        logger.info(f"Successfully loaded {loaded_count} YAML protocols from {directory}")
        return loaded_count

    def load_from_file(self, file_path: str) -> Optional[YamlProtocolTemplate]:
        """
        从单个文件加载YAML协议

        Args:
            file_path: YAML协议文件路径

        Returns:
            加载的协议模板，如果失败返回None
        """
        try:
            template = self._load_yaml_file(file_path)
            if template:
                self.loaded_templates[template.protocol_id] = template
                self._save_to_database(template)
                self._load_to_converter(template)
                logger.info(f"Loaded YAML protocol: {template.protocol_id} from {file_path}")
                return template
            return None
        except Exception as e:
            logger.error(f"Error loading YAML file {file_path}: {e}")
            return None

    def _find_yaml_files(self, directory: str) -> List[str]:
        """查找所有YAML协议文件"""
        yaml_files = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.yaml') and not file.endswith('.meta.yaml'):
                    yaml_files.append(os.path.join(root, file))

        return sorted(yaml_files)

    def _load_yaml_file(self, file_path: str) -> Optional[YamlProtocolTemplate]:
        """
        加载单个YAML协议文件

        Args:
            file_path: YAML文件路径

        Returns:
            YAML协议模板，如果失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()

            # 检查是否是纯模板文件（不包含metadata）
            if 'metadata:' in yaml_content:
                logger.warning(f"Skipping metadata file: {file_path}")
                return None

            # 解析协议ID和协议族
            protocol_id = self._extract_protocol_id(file_path)
            if not protocol_id:
                logger.error(f"Cannot extract protocol ID from filename: {file_path}")
                return None

            family = self._extract_protocol_family(protocol_id)
            if not family:
                logger.error(f"Cannot extract protocol family from protocol ID: {protocol_id}")
                return None

            # 使用YamlProcessor安全地转换YAML为Python对象
            template_data, placeholder_map = self._convert_yaml_to_data(yaml_content)

            # 生成schema和变量映射
            protected_data, _ = self.yaml_processor.protect_jinja_syntax(template_data, placeholder_map)
            schema = self.schema_generator.generate_schema(protected_data, placeholder_map)
            variable_mapping = self.variable_mapper.map_variables(protected_data, placeholder_map)

            # 验证YAML结构
            validation_result = self._validate_yaml_structure(template_data, schema)

            # 创建YAML协议模板对象
            template = YamlProtocolTemplate(
                protocol_id=protocol_id,
                family=family,
                file_path=file_path,
                yaml_content=yaml_content,
                template_data=template_data,
                schema=schema,
                variable_mapping=variable_mapping,
                jinja_placeholders=placeholder_map,
                validation_result=validation_result,
                metadata={
                    'file_size': len(yaml_content),
                    'jinja_variables_count': len(variable_mapping.regular_variables),
                    'special_variables_count': len(variable_mapping.special_variables),
                    'schema_properties_count': len(schema.get('properties', {}))
                }
            )

            return template

        except Exception as e:
            logger.error(f"Error processing YAML file {file_path}: {e}")
            return None

    def _convert_yaml_to_data(self, yaml_content: str) -> Tuple[Dict[str, Any], Dict[str, Jinja2Placeholder]]:
        """
        安全地将YAML内容转换为Python对象

        Args:
            yaml_content: YAML内容字符串

        Returns:
            (Python字典对象, Jinja2占位符映射)的元组
        """
        try:
            # 首先尝试直接解析
            parsed_data = yaml.safe_load(yaml_content)

            # 检查是否包含Jinja2语法，即使解析成功
            if self.yaml_processor.variable_pattern.search(yaml_content):
                logger.debug("YAML parsed successfully but contains Jinja2 syntax, extracting variables...")
                placeholder_map = self.yaml_processor._extract_jinja_from_yaml(yaml_content)
                return parsed_data, placeholder_map
            else:
                return parsed_data, {}

        except yaml.YAMLError as e:
            # 如果解析失败，说明包含Jinja2语法
            logger.debug(f"Direct YAML parsing failed, trying with Jinja2 protection: {e}")

            # 使用YamlProcessor的方法
            try:
                # 这是一个简化的实现，因为yaml_to_json有问题
                # 我们手动处理Jinja2语法
                placeholder_map = self.yaml_processor._extract_jinja_from_yaml(yaml_content)
                protected_yaml = self.yaml_processor._protect_yaml_content(yaml_content, placeholder_map)
                parsed_data = yaml.safe_load(protected_yaml)

                return parsed_data, placeholder_map
            except Exception as e2:
                logger.error(f"Failed to parse YAML even with Jinja2 protection: {e2}")
                raise ValueError(f"Cannot parse YAML content: {e2}")

    def _validate_yaml_structure(self, data: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """
        验证YAML结构

        Args:
            data: YAML数据
            schema: YAML schema

        Returns:
            验证结果
        """
        try:
            return self.schema_generator.validate_data(data, schema, strict_mode=False)
        except Exception as e:
            logger.warning(f"Schema validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Schema validation error: {str(e)}"],
                warnings=[],
                matched_paths=[],
                unmatched_paths=[]
            )

    def _extract_protocol_id(self, file_path: str) -> Optional[str]:
        """从文件路径提取协议ID"""
        filename = os.path.basename(file_path)
        return os.path.splitext(filename)[0]

    def _extract_protocol_family(self, protocol_id: str) -> Optional[str]:
        """从协议ID中提取协议族"""
        # 匹配格式：字母-数字（如 A-1, B-2, C-3）
        if '-' in protocol_id:
            return protocol_id.split('-')[0]
        return None

    def _save_to_database(self, template: YamlProtocolTemplate) -> bool:
        """保存到数据库"""
        try:
            # 将变量映射转换为JSON格式
            variables = list(template.variable_mapping.regular_variables)
            special_variables = list(template.variable_mapping.special_variables)

            # 将schema转换为JSON字符串
            schema_json = json.dumps(template.schema, ensure_ascii=False, indent=2)

            # 将变量路径映射转换为JSON
            variable_paths = {
                name: info.yaml_paths
                for name, info in template.variable_mapping.variable_map.items()
            }
            variable_paths_json = json.dumps(variable_paths, ensure_ascii=False, indent=2)

            success = self.db.save_protocol(
                protocol_id=template.protocol_id,
                protocol_family=template.family,
                template_content=template.yaml_content,
                variables=variables,
                special_variables=special_variables,
                raw_schema=schema_json,
                variable_paths=variable_paths_json
            )

            return success

        except Exception as e:
            logger.error(f"Failed to save protocol {template.protocol_id} to database: {e}")
            return False

    def _load_to_converter(self, template: YamlProtocolTemplate) -> bool:
        """加载到转换器"""
        try:
            # 提取变量和特殊变量
            variables = list(template.variable_mapping.regular_variables)
            special_variables = list(template.variable_mapping.special_variables)

            # 检查数组标记
            array_markers = []
            for var_name, var_info in template.variable_mapping.variable_map.items():
                # 检查是否是数组相关的变量
                if 'array' in var_name.lower() or any('array' in path for path in var_info.yaml_paths):
                    # 简化的数组标记检测
                    array_markers.append(ArrayMarker(
                        field_path=var_info.yaml_paths[0] if var_info.yaml_paths else var_name,
                        is_dynamic=True,
                        template_item={}
                    ))

            # 创建ProtocolTemplate对象
            simple_template = ProtocolTemplate(
                protocol_id=template.protocol_id,
                protocol_family=template.family,
                template_content=template.template_data,  # 使用解析后的数据
                variables=variables,
                special_variables=special_variables,
                array_markers=array_markers
            )

            # 加载到转换器
            self.converter.load_protocol(
                protocol_id=template.protocol_id,
                protocol_family=template.family,
                template=simple_template
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load protocol {template.protocol_id} to converter: {e}")
            return False

    def get_template(self, protocol_id: str) -> Optional[YamlProtocolTemplate]:
        """获取已加载的协议模板"""
        return self.loaded_templates.get(protocol_id)

    def get_all_templates(self) -> Dict[str, YamlProtocolTemplate]:
        """获取所有已加载的协议模板"""
        return self.loaded_templates.copy()

    def get_templates_by_family(self, family: str) -> List[YamlProtocolTemplate]:
        """根据协议族获取协议模板"""
        return [template for template in self.loaded_templates.values()
                if template.family == family]

    def search_templates(self, **criteria) -> List[YamlProtocolTemplate]:
        """
        根据条件搜索协议模板

        Args:
            **criteria: 搜索条件 (protocol_id, family等)

        Returns:
            匹配的协议模板列表
        """
        results = []

        for template in self.loaded_templates.values():
            match = True

            for key, value in criteria.items():
                if hasattr(template, key):
                    if getattr(template, key) != value:
                        match = False
                        break

            if match:
                results.append(template)

        return results

    def validate_all_templates(self) -> Dict[str, ValidationResult]:
        """验证所有已加载的模板"""
        results = {}

        for protocol_id, template in self.loaded_templates.items():
            if template.validation_result:
                results[protocol_id] = template.validation_result
            else:
                # 如果没有验证结果，重新验证
                results[protocol_id] = self._validate_yaml_structure(
                    template.template_data, template.schema
                )

        return results

    def reload_template(self, protocol_id: str) -> bool:
        """重新加载指定的协议模板"""
        if protocol_id not in self.loaded_templates:
            logger.warning(f"Protocol {protocol_id} not found in loaded templates")
            return False

        template = self.loaded_templates[protocol_id]
        file_path = template.file_path

        # 从文件重新加载
        try:
            new_template = self._load_yaml_file(file_path)
            if new_template:
                self.loaded_templates[protocol_id] = new_template
                self._save_to_database(new_template)
                self._load_to_converter(new_template)
                logger.info(f"Reloaded protocol: {protocol_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to reload protocol {protocol_id}: {e}")

        return False

    def get_loaded_protocols(self) -> List[str]:
        """获取已加载的协议列表"""
        return list(self.loaded_templates.keys())

    def get_protocol_families(self) -> List[str]:
        """获取协议族列表"""
        families = set()
        for template in self.loaded_templates.values():
            families.add(template.family)
        return sorted(list(families))

    def get_converter(self) -> ProtocolConverter:
        """获取转换器实例"""
        return self.converter

    def get_statistics(self) -> Dict[str, Any]:
        """获取加载统计信息"""
        total_templates = len(self.loaded_templates)
        families = self.get_protocol_families()

        total_variables = 0
        total_special_variables = 0

        for template in self.loaded_templates.values():
            total_variables += len(template.variable_mapping.regular_variables)
            total_special_variables += len(template.variable_mapping.special_variables)

        return {
            'total_templates': total_templates,
            'total_families': len(families),
            'families': families,
            'total_variables': total_variables,
            'total_special_variables': total_special_variables,
            'avg_variables_per_template': total_variables / total_templates if total_templates > 0 else 0
        }

def create_yaml_loader(db_path: str = "protocols.db",
                        yaml_dir: str = "./protocols_yaml") -> YamlProtocolLoader:
    """
    创建YAML协议加载器实例的便利函数

    Args:
        db_path: 数据库路径
        yaml_dir: YAML文件目录路径

    Returns:
        YamlProtocolLoader实例
    """
    return YamlProtocolLoader(db_path, yaml_dir)