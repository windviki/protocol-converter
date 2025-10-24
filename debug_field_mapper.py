#!/usr/bin/env python3
"""
调试field mapper的具体问题
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

def debug_field_mapper():
    """调试field mapper的具体问题"""
    print("🔍 调试Field Mapper")
    print("=" * 50)

    # 创建field mapper
    field_mapper = create_field_mapper()

    # 检查mapping config
    print(f"Mapping config: {field_mapper.mapping_config}")

    # 检查A-4 <-> B-4的具体配置
    a4_b4_config = field_mapper.mapping_config.get('A-4 <-> B-4', {})
    print(f"A-4 <-> B-4 config: {a4_b4_config}")
    print(f"Config type: {type(a4_b4_config)}")

    # 检查每个rule
    for rule_name, rule_config in a4_b4_config.items():
        print(f"Rule {rule_name}: {rule_config}")
        print(f"  from: {rule_config.get('from')} (type: {type(rule_config.get('from'))})")
        print(f"  to: {rule_config.get('to')} (type: {type(rule_config.get('to'))})")

if __name__ == "__main__":
    debug_field_mapper()