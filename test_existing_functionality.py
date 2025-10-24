#!/usr/bin/env python3
"""
测试现有协议转换功能
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_database
from protocol_manager.manager import ProtocolManager
from core.converter import ProtocolConverter
from converters.functions import CONVERTER_FUNCTIONS


def test_existing_functionality():
    """测试现有的协议转换功能"""
    print("=" * 50)
    print("现有协议转换功能测试")
    print("=" * 50)

    try:
        # 1. 初始化数据库
        print("\n1. 初始化数据库...")
        init_database()
        print("[OK] 数据库初始化成功")

        # 2. 加载协议文件
        print("\n2. 加载协议文件...")
        manager = ProtocolManager()
        result = manager.load_protocols_from_directory("./examples/protocols")

        print(f"[OK] 加载结果: {result['loaded_files']} 个文件成功, {result['failed_files']} 个文件失败")

        # 3. 列出协议族
        print("\n3. 列出协议族...")
        families = manager.list_all_families()
        print("[OK] 可用协议族:", families)

        # 4. 创建转换器
        print("\n4. 创建转换器...")
        converter = ProtocolConverter(CONVERTER_FUNCTIONS)

        # 加载协议到转换器
        for family in families:
            protocols = manager.get_protocols_by_family(family)
            for protocol_id in protocols:
                protocol_info = manager.get_protocol_by_id(protocol_id)
                if protocol_info:
                    converter.load_protocol(
                        protocol_id=protocol_id,
                        protocol_family=protocol_info['family'],
                        template_content=protocol_info['template']
                    )

        # 5. 测试A到C转换
        print("\n5. 测试A到C转换...")
        with open("./examples/input/A-1-input.json", "r", encoding="utf-8") as f:
            test_input = json.load(f)

        print("输入数据:", json.dumps(test_input, ensure_ascii=False, indent=2))

        result = converter.convert("A", "C", test_input)

        if result.success:
            print("[OK] A到C转换成功")
            print("匹配协议:", result.matched_protocol)
            print("提取变量:", result.variables)
            print("转换结果:")
            print(json.dumps(result.result, ensure_ascii=False, indent=2))
        else:
            print("[ERROR] A到C转换失败:", result.error)

        return result.success

    except Exception as e:
        print(f"[ERROR] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_existing_functionality()
    sys.exit(0 if success else 1)