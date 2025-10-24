#!/usr/bin/env python3
"""
简单的YAML转换测试脚本
用于调试Jinja2语法保护机制
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.yaml_processor import YamlProcessor

def test_simple_conversion():
    """测试简单的JSON到YAML转换"""

    # 测试数据（包含Jinja2语法）
    test_json = {
        "domain": "telephone",
        "action": "DIAL",
        "slots": {
            "category": "{{ phone_type }}",
            "name": "{{ person }}"
        }
    }

    print("原始JSON:")
    print(json.dumps(test_json, indent=2))
    print()

    # 创建处理器
    processor = YamlProcessor()

    try:
        # 测试Jinja2语法保护
        print("测试Jinja2语法保护...")
        protected_data, placeholder_map = processor.protect_jinja_syntax(test_json)
        print("保护后的数据:")
        print(json.dumps(protected_data, indent=2))
        print(f"占位符数量: {len(placeholder_map)}")
        for pid, info in placeholder_map.items():
            print(f"  {pid}: {info.original_content}")
        print()

        # 测试JSON到YAML转换
        print("测试JSON到YAML转换...")
        yaml_content = processor.json_to_yaml(test_json)
        print("转换后的YAML:")
        print(yaml_content)
        print()

        # 测试YAML解析（需要先保护Jinja2语法）
        print("测试YAML解析（先保护Jinja2语法）...")

        # 从YAML内容中提取Jinja2语法并保护
        placeholder_map_from_yaml = {}
        for line in yaml_content.split('\n'):
            for match in processor.variable_pattern.finditer(line):
                if processor.variable_pattern.search(line):
                    # 手动创建占位符映射
                    import re
                    pattern = re.compile(r'\{\{\s*([^{}]+?)\s*\}\}')
                    for m in pattern.finditer(line):
                        pid = f"__PLACEHOLDER_{len(placeholder_map_from_yaml)}__"
                        placeholder_map_from_yaml[pid] = m.group(0)

        # 简单替换（仅用于测试）
        protected_yaml = yaml_content
        for pid, jinja_content in placeholder_map_from_yaml.items():
            protected_yaml = protected_yaml.replace(jinja_content, pid)

        print("受保护的YAML:")
        print(protected_yaml)
        print()

        import yaml
        parsed_data = yaml.safe_load(protected_yaml)
        print("解析后的数据:")
        print(json.dumps(parsed_data, indent=2))
        print()

        # 检查是否一致
        if parsed_data == protected_data:
            print("✅ 转换成功！")
        else:
            print("❌ 转换失败，数据不一致")

        print("\n注意：YAML文件存储时可以包含Jinja2语法，")
        print("但程序内部处理时需要先保护Jinja2语法再解析YAML。")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_conversion()