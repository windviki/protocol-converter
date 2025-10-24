#!/usr/bin/env python3
"""
调试mapping变量识别
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.yaml_processor import YamlProcessor
from utils.variable_mapper import VariableMapper

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_mapping():
    """调试mapping变量识别"""
    print("🔍 调试mapping变量识别")
    print("=" * 50)

    # 模拟A-4模板内容
    yaml_content = """
domain: navigation
action: ROUTE_TO
slots:
  destination: ${{destination}}
  poi_type: ${{poi_type}}
  vehicle_type: {{ vehicle_type }}
"""

    print(f"原始YAML内容:")
    print(yaml_content)

    # 使用YamlProcessor处理
    processor = YamlProcessor()

    # 1. 提取Jinja2语法
    print(f"\n📝 提取Jinja2语法:")
    placeholder_map = processor._extract_jinja_from_yaml(yaml_content)
    print(f"占位符映射: {placeholder_map}")

    for placeholder_id, placeholder_info in placeholder_map.items():
        print(f"  {placeholder_id}: {placeholder_info.original_content}")

    # 2. 保护YAML内容
    protected_yaml = processor._protect_yaml_content(yaml_content, placeholder_map)
    print(f"\n🛡️ 保护后的YAML:")
    print(protected_yaml)

    # 3. 转换为Python对象
    import yaml
    try:
        template_data = yaml.safe_load(protected_yaml)
        print(f"\n🐍 转换后的Python对象:")
        print(template_data)
    except Exception as e:
        print(f"❌ YAML解析失败: {e}")
        return

    # 4. 使用VariableMapper处理
    print(f"\n🔍 使用VariableMapper处理:")
    mapper = VariableMapper()

    result = mapper.map_variables(template_data, placeholder_map)

    print(f"映射结果:")
    print(f"  正则变量: {result.regular_variables}")
    print(f"  特殊变量: {result.special_variables}")
    print(f"  映射变量: {result.mapping_variables}")

    print(f"\n详细变量映射:")
    for var_name, var_info in result.variable_map.items():
        print(f"  {var_name}: type={var_info.variable_type}, paths={var_info.yaml_paths}, expr='{var_info.jinja_expression}'")

if __name__ == "__main__":
    debug_mapping()