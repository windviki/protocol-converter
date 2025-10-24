#!/usr/bin/env python3
"""
测试field mapping功能
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.yaml_processor import YamlProcessor
from utils.variable_mapper import VariableMapper
from core.field_mapper import create_field_mapper

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_field_mapping():
    """测试field mapping功能"""
    print("🧪 测试Field Mapping功能")
    print("=" * 50)

    # 1. 测试数据
    source_data = {
        "destination": "人民路与中山路交叉口",
        "poi_type": "intersection",
        "vehicle_type": "car"
    }

    print(f"源数据: {source_data}")

    # 2. 测试split_intersection处理器
    print(f"\n🔧 测试split_intersection处理器:")
    field_mapper = create_field_mapper()

    split_result = field_mapper.split_intersection(source_data["destination"])
    print(f"  分割结果: {split_result}")

    # 3. 测试combine_intersection处理器
    print(f"\n🔧 测试combine_intersection处理器:")
    combine_result = field_mapper.combine_intersection("人民路", "中山路")
    print(f"  合并结果: {combine_result}")

    # 4. 测试完整的mapping过程
    print(f"\n🔄 测试完整的mapping过程 (A-4 -> B-4):")

    # 模拟mapping变量
    mapping_vars = {
        "destination": source_data["destination"],
        "poi_type": source_data["poi_type"]
    }

    mapped_vars = field_mapper.process_mapping(
        mapping_vars, "A-4", "B-4", source_data
    )

    print(f"  映射变量: {mapping_vars}")
    print(f"  映射结果: {mapped_vars}")

    # 5. 测试反向mapping (B-4 -> A-4)
    print(f"\n🔄 测试反向mapping (B-4 -> A-4):")

    b4_data = {
        "intersection": {
            "primary_road": "人民路",
            "secondary_road": "中山路"
        }
    }

    mapping_vars_reverse = {
        "intersection.primary_road": b4_data["intersection"]["primary_road"],
        "intersection.secondary_road": b4_data["intersection"]["secondary_road"]
    }

    mapped_vars_reverse = field_mapper.process_mapping(
        mapping_vars_reverse, "B-4", "A-4", b4_data
    )

    print(f"  反向映射变量: {mapping_vars_reverse}")
    print(f"  反向映射结果: {mapped_vars_reverse}")

    print(f"\n✅ Field mapping测试完成!")

if __name__ == "__main__":
    test_field_mapping()