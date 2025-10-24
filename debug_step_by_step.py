#!/usr/bin/env python3
"""
逐步调试field mapping过程
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.field_mapper import create_field_mapper

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_step_by_step():
    """逐步调试field mapping过程"""
    print("🔍 逐步调试Field Mapping")
    print("=" * 50)

    # 创建field mapper
    field_mapper = create_field_mapper()

    # 测试数据
    mapping_vars = {
        "destination": "人民路与中山路交叉口"
    }
    source_data = {
        "destination": "人民路与中山路交叉口"
    }

    print(f"输入数据: {mapping_vars}")

    # 手动处理destination_to_intersection规则
    rule_name = "destination_to_intersection"
    rule_config = {
        'from': 'destination',
        'to': ['intersection.primary_road', 'intersection.secondary_road'],
        'processor': 'split_intersection',
        'description': '将目的地字符串分割为主路和次路'
    }

    print(f"\n处理规则: {rule_name}")
    print(f"规则配置: {rule_config}")

    # 获取处理器
    processor_name = rule_config.get('processor', 'direct_mapping')
    processor = field_mapper.processors.get(processor_name)
    print(f"处理器: {processor_name} -> {processor}")

    # 获取源模式
    source_pattern = rule_config.get('from')
    print(f"源模式: {source_pattern} (type: {type(source_pattern)})")

    if isinstance(source_pattern, str):
        print("处理字符串源模式...")
        source_value = field_mapper._extract_field_value(source_pattern, mapping_vars, source_data)
        print(f"提取的源值: {source_value}")

        result_value = processor(source_value)
        print(f"处理器结果: {result_value}")

        target_path = rule_config.get('to')
        print(f"目标路径: {target_path} (type: {type(target_path)})")

        if isinstance(target_path, list):
            result_dict = dict(zip(target_path, result_value)) if isinstance(result_value, list) else {target_path[0]: result_value}
            print(f"最终结果: {result_dict}")

if __name__ == "__main__":
    debug_step_by_step()