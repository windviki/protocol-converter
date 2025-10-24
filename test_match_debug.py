#!/usr/bin/env python3
"""
调试协议匹配问题
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from protocols.yaml_loader import create_yaml_loader

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_matching():
    """调试协议匹配问题"""
    print("🔍 调试协议匹配")
    print("=" * 50)

    try:
        # 创建YAML加载器
        loader = create_yaml_loader()
        loaded_count = loader.load_from_directory()
        print(f"加载了 {loaded_count} 个协议")

        # 获取转换器和匹配器
        converter = loader.get_converter()
        matcher = converter.matcher

        # 测试输入数据
        test_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        print(f"\n📥 测试输入:")
        print(f"  domain: {test_input['domain']}")
        print(f"  action: {test_input['action']}")
        print(f"  slots: {test_input['slots']}")

        # 检查A族协议
        print(f"\n🏷️ 检查A族协议:")
        a_family_protocols = {pid: p for pid, p in matcher.protocols.items()
                            if p.protocol_family == "A"}

        for protocol_id, protocol in a_family_protocols.items():
            print(f"\n  协议: {protocol_id}")
            print(f"  模板内容: {protocol.template_content}")
            print(f"  变量列表: {protocol.variables}")

            # 手动测试匹配
            is_match = matcher._is_match(protocol.template_content, test_input)
            print(f"  匹配结果: {is_match}")

            # 测试清理后的模板
            cleaned_template = matcher._clean_template_for_matching(protocol.template_content)
            print(f"  清理后模板: {cleaned_template}")

        # 运行实际匹配
        print(f"\n🔄 运行实际匹配:")
        matched_protocol_id = matcher.match_protocol("A", test_input)
        print(f"  匹配的协议: {matched_protocol_id}")

    except Exception as e:
        logger.exception("调试失败")
        print(f"❌ 调试失败: {e}")

if __name__ == "__main__":
    debug_matching()