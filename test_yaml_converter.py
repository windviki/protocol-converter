#!/usr/bin/env python3
"""
测试YAML协议转换器的完整流程
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

def test_yaml_conversion():
    """测试YAML协议转换的完整流程"""
    print("🔄 测试YAML协议转换流程")
    print("=" * 50)

    try:
        # 创建YAML加载器
        logger.info("Creating YAML loader...")
        loader = create_yaml_loader()

        # 加载所有协议
        logger.info("Loading protocols from YAML files...")
        loaded_count = loader.load_from_directory()

        print(f"\n✅ 成功加载了 {loaded_count} 个YAML协议")

        # 获取转换器
        converter = loader.get_converter()

        # 测试输入数据（电话拨号）
        test_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        print(f"\n📥 测试输入数据:")
        print(f"  domain: {test_input['domain']}")
        print(f"  action: {test_input['action']}")
        print(f"  slots.name: {test_input['slots']['name']}")
        print(f"  slots.category: {test_input['slots']['category']}")

        # 尝试转换：从A族协议转换为B族协议
        print(f"\n🔄 尝试协议转换: A -> B")

        try:
            result = converter.convert("A", "B", test_input)

            if result.success:
                print(f"✅ 转换成功!")
                print(f"  匹配的协议: {result.matched_protocol}")
                print(f"  提取的变量: {result.variables}")
                if result.result:
                    print(f"  转换结果:")
                    for key, value in result.result.items():
                        print(f"    {key}: {value}")
                else:
                    print(f"  转换结果: None")
            else:
                print(f"❌ 转换失败: {result.error}")

        except Exception as e:
            print(f"❌ 转换异常: {e}")
            logger.exception("Conversion failed")

        # 列出加载的协议
        print(f"\n📋 已加载的协议列表:")
        for protocol_id in sorted(loader.get_loaded_protocols()):
            template = loader.get_template(protocol_id)
            if template:
                print(f"  - {protocol_id} (族: {template.family}, 变量: {len(template.variable_mapping.regular_variables)})")

        print(f"\n🎉 YAML转换流程测试完成！")
        return True

    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_yaml_conversion()