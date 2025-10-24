#!/usr/bin/env python3
"""
测试占位符恢复机制
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from protocols.yaml_loader import create_yaml_loader
from core.renderer import TemplateRenderer

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_placeholder_restore():
    """测试占位符恢复功能"""
    print("🔧 测试占位符恢复机制")
    print("=" * 50)

    try:
        # 创建YAML加载器
        loader = create_yaml_loader()
        loaded_count = loader.load_from_directory()
        print(f"加载了 {loaded_count} 个协议")

        # 获取A-1协议
        a1_template = loader.get_template("A-1")
        if a1_template:
            print(f"\n📋 A-1协议信息:")
            print(f"  协议ID: {a1_template.protocol_id}")
            print(f"  变量数: {len(a1_template.variable_mapping.regular_variables)}")
            print(f"  占位符数: {len(a1_template.jinja_placeholders)}")

            print(f"\n🔍 模板内容（包含占位符）:")
            print(f"  {a1_template.template_data}")

            print(f"\n📝 占位符映射:")
            for placeholder_id, placeholder_info in a1_template.jinja_placeholders.items():
                print(f"  {placeholder_id} -> {placeholder_info.original_content}")

            # 创建渲染器并测试占位符恢复
            renderer = TemplateRenderer({})

            print(f"\n🔄 测试占位符恢复:")
            restored = renderer._restore_jinja_placeholders(
                a1_template.template_data,
                a1_template.jinja_placeholders
            )
            print(f"  恢复后的模板: {restored}")

        else:
            print("❌ 未找到A-1协议")

    except Exception as e:
        logger.exception("测试失败")
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_placeholder_restore()