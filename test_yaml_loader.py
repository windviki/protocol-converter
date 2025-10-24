#!/usr/bin/env python3
"""
测试YAML协议加载器
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from protocols.yaml_loader import create_yaml_loader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_yaml_loader():
    """测试YAML加载器功能"""
    print("🧪 测试YAML协议加载器")
    print("=" * 50)

    try:
        # 创建YAML加载器
        logger.info("Creating YAML loader...")
        loader = create_yaml_loader()

        # 加载所有协议
        logger.info("Loading protocols from YAML files...")
        loaded_count = loader.load_from_directory()

        print(f"\n✅ 成功加载了 {loaded_count} 个YAML协议")

        # 获取统计信息
        stats = loader.get_statistics()
        print(f"\n📊 加载统计:")
        print(f"  总协议数: {stats['total_templates']}")
        print(f"  协议族数: {stats['total_families']}")
        print(f"  协议族: {', '.join(stats['families'])}")
        print(f"  总变量数: {stats['total_variables']}")
        print(f"  特殊变量数: {stats['total_special_variables']}")
        print(f"  平均变量数: {stats['avg_variables_per_template']:.1f}")

        # 显示加载的协议
        print(f"\n📋 已加载的协议:")
        for protocol_id in sorted(loader.get_loaded_protocols()):
            template = loader.get_template(protocol_id)
            if template:
                print(f"  - {protocol_id} (族: {template.family})")

        # 测试获取特定协议
        print(f"\n🔍 测试获取特定协议 A-1:")
        a1_template = loader.get_template("A-1")
        if a1_template:
            print(f"  协议ID: {a1_template.protocol_id}")
            print(f"  协议族: {a1_template.family}")
            print(f"  变量数: {len(a1_template.variable_mapping.regular_variables)}")
            print(f"  特殊变量数: {len(a1_template.variable_mapping.special_variables)}")
            print(f"  YAML内容长度: {len(a1_template.yaml_content)} 字符")
            print(f"  验证状态: {'✅ 通过' if a1_template.validation_result.is_valid else '❌ 失败'}")

            # 显示前几个变量
            regular_vars = []
            if a1_template.variable_mapping.regular_variables:
                regular_vars = list(a1_template.variable_mapping.regular_variables)
                print(f"  普通变量: {', '.join(regular_vars[:5])}")
            if a1_template.variable_mapping.special_variables:
                special_vars = list(a1_template.variable_mapping.special_variables)
                print(f"  特殊变量: {', '.join(special_vars[:5])}")
        else:
            print("  ❌ 未找到A-1协议")

        # 按协议族分组显示
        print(f"\n🏷️ 按协议族分组:")
        for family in loader.get_protocol_families():
            family_templates = loader.get_templates_by_family(family)
            print(f"  {family}族: {len(family_templates)} 个协议")
            for template in family_templates[:3]:  # 只显示前3个
                print(f"    - {template.protocol_id}")

        # 验证所有模板
        print(f"\n🔍 验证所有模板结构:")
        validation_results = loader.validate_all_templates()
        valid_count = sum(1 for r in validation_results.values() if r.is_valid)
        total_count = len(validation_results)
        print(f"  验证通过: {valid_count}/{total_count}")

        # 显示有验证问题的协议
        if valid_count < total_count:
            print(f"\n⚠️ 验证失败的协议:")
            for protocol_id, result in validation_results.items():
                if not result.is_valid:
                    print(f"  - {protocol_id}: {len(result.errors)} 个错误")

        print(f"\n🎉 YAML加载器测试完成！")
        return True

    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_yaml_loader()