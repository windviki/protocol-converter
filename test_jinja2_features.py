#!/usr/bin/env python3
"""
Jinja2功能测试脚本
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


def test_jinja2_features():
    """测试Jinja2功能"""
    print("=" * 50)
    print("Jinja2功能测试")
    print("=" * 50)

    try:
        # 1. 初始化数据库
        print("\n1. 初始化数据库...")
        init_database()
        print("[OK] 数据库初始化成功")

        # 2. 加载测试协议文件
        print("\n2. 加载测试协议文件...")
        manager = ProtocolManager()
        result = manager.load_protocols_from_directory("./examples/protocols")

        print(f"[OK] 加载结果: {result['loaded_files']} 个文件成功, {result['failed_files']} 个文件失败")

        if result['loaded_files'] == 0:
            print("[ERROR] 没有成功加载任何协议文件")
            return False

        # 3. 列出协议族
        print("\n3. 列出协议族...")
        families = manager.list_all_families()
        print("[OK] 可用协议族:", families)

        # 4. 列出协议
        print("\n4. 列出协议...")
        for family in families:
            protocols = manager.get_protocols_by_family(family)
            print("[OK] 协议族", family, ":", protocols)

        # 5. 测试协议转换
        print("\n5. 测试协议转换...")

        # 创建转换器
        converter = ProtocolConverter(CONVERTER_FUNCTIONS)
        print("转换器创建成功")

        # 加载协议到转换器
        for family in families:
            protocols = manager.get_protocols_by_family(family)
            print(f"协议族 {family} 的协议: {protocols}")
            for protocol_id in protocols:
                protocol_info = manager.get_protocol_by_id(protocol_id)
                if protocol_info:
                    print(f"加载协议 {protocol_id} 到转换器")
                    converter.load_protocol(
                        protocol_id=protocol_id,
                        protocol_family=protocol_info['family'],
                        template_content=protocol_info['template']
                    )

        # 测试输入数据
        with open("./examples/input/TestA-1-input.json", "r", encoding="utf-8") as f:
            test_input = json.load(f)

        print("输入数据:", json.dumps(test_input, ensure_ascii=False, indent=2))

        # 执行转换 TestA -> TestC
        print("\n转换 TestA -> TestC:")
        result = converter.convert("TestA", "TestC", test_input)

        if result.success:
            print("[OK] 转换成功")
            print("匹配协议:", result.matched_protocol)
            print("提取变量:", result.variables)
            print("转换结果:")
            print(json.dumps(result.result, ensure_ascii=False, indent=2))

            # 验证结果
            expected_keys = ["operation", "item_names", "item_count", "primary_items"]
            if all(key in result.result for key in expected_keys):
                print("[OK] 结果结构正确")

                # 检查length filter
                if result.result["item_count"] == "3":
                    print("[OK] length filter工作正常")
                else:
                    print("[ERROR] length filter工作异常")

                # 检查for循环和if语句
                expected_item_names = "item1, item2, item3"
                if result.result["item_names"] == expected_item_names:
                    print("[OK] for循环和if not loop.last工作正常")
                else:
                    print("[ERROR] for循环或if not loop.last工作异常")

                # 检查for循环中的条件语句
                expected_primary_items = "item1, item3"
                if result.result["primary_items"] == expected_primary_items:
                    print("[OK] for循环中的条件语句工作正常")
                else:
                    print("[ERROR] for循环中的条件语句工作异常")

                return True
            else:
                print("[ERROR] 结果结构不正确")
                print("期望的字段:", expected_keys)
                print("实际的字段:", list(result.result.keys()))
                return False
        else:
            print("[ERROR] 转换失败:", result.error)
            return False

    except Exception as e:
        print(f"[ERROR] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_jinja2_features()
    sys.exit(0 if success else 1)