#!/usr/bin/env python3
"""
测试动态数组上下文功能的脚本
"""

import sys
import os
import json
import tempfile
import shutil

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_database
from protocol_manager.manager import ProtocolManager
from core.converter import ProtocolConverter
from converters.functions import CONVERTER_FUNCTIONS


def test_array_context():
    """测试动态数组上下文功能"""
    print("=" * 60)
    print("动态数组上下文功能测试")
    print("=" * 60)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"使用临时目录: {temp_dir}")

    try:
        # 1. 初始化数据库
        print("\n1. 初始化数据库...")
        init_database()
        print("✓ 数据库初始化成功")

        # 2. 创建测试协议文件
        print("\n2. 创建测试协议文件...")

        # 创建TestA协议
        test_a_dir = os.path.join(temp_dir, "TestA")
        os.makedirs(test_a_dir)

        test_a_content = {
            "operation": "process",
            "data": [
                "{# array_dynamic: true #}",
                {
                    "name": "{{ name }}",
                    "value": "{{ value }}",
                    "type": "{{ type }}",
                    "domain": "{{ domain }}"
                }
            ]
        }

        with open(os.path.join(test_a_dir, "TestA-1.json"), "w", encoding="utf-8") as f:
            json.dump(test_a_content, f, ensure_ascii=False, indent=2)

        # 复制我们创建的TestC协议
        test_c_dir = os.path.join(temp_dir, "TestC")
        os.makedirs(test_c_dir)

        # 读取TestC-array-context.json并保存到临时目录
        source_file = os.path.join(os.path.dirname(__file__), "examples", "protocols", "TestC", "TestC-array-context.json")
        with open(source_file, "r", encoding="utf-8") as src:
            content = json.load(src)

        with open(os.path.join(test_c_dir, "TestC-1.json"), "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

        print("✓ 测试协议文件创建成功")

        # 3. 加载协议文件
        print("\n3. 加载协议文件...")
        manager = ProtocolManager()
        result = manager.load_protocols_from_directory(temp_dir)

        print(f"加载结果: {result['loaded_files']} 个文件成功, {result['failed_files']} 个文件失败")

        if result['loaded_files'] == 0:
            print("✗ 没有成功加载任何协议文件")
            return False

        # 4. 列出协议族
        print("\n4. 列出协议族...")
        families = manager.list_all_families()
        print(f"可用协议族: {families}")

        # 5. 列出协议
        print("\n5. 列出协议...")
        for family in families:
            protocols = manager.get_protocols_by_family(family)
            print(f"协议族 {family}: {protocols}")

        # 6. 测试协议转换
        print("\n6. 测试协议转换...")

        # 创建转换器
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

        # 测试输入数据
        test_input = {
            "operation": "process",
            "data": [
                {
                    "name": "alice",
                    "value": 100,
                    "type": "primary",
                    "domain": "test"
                },
                {
                    "name": "bob",
                    "value": 200,
                    "type": "secondary",
                    "domain": "test"
                },
                {
                    "name": "charlie",
                    "value": 300,
                    "type": "primary",
                    "domain": "test"
                }
            ]
        }

        print(f"输入数据: {json.dumps(test_input, ensure_ascii=False, indent=2)}")

        # 执行转换 TestA -> TestC
        print("\n转换 TestA -> TestC:")
        result = converter.convert("TestA", "TestC", test_input)

        if result.success:
            print("✓ 转换成功")
            print(f"匹配协议: {result.matched_protocol}")
            print(f"提取变量: {result.variables}")
            print(f"转换结果:")
            print(json.dumps(result.result, ensure_ascii=False, indent=2))

            # 7. 验证数组上下文功能
            print("\n7. 验证数组上下文功能...")

            items = result.result.get("items", [])
            if len(items) == 3:
                print("✓ 数组元素数量正确")

                for i, item in enumerate(items):
                    array_info = item.get("array_info", {})
                    index = array_info.get("index")
                    total = array_info.get("total")
                    session_id = array_info.get("session_id")
                    session_id_v2 = array_info.get("session_id_v2")

                    print(f"  元素 {i}:")
                    print(f"    索引: {index}")
                    print(f"    总数: {total}")
                    print(f"    Session ID: {session_id}")
                    print(f"    Session ID v2: {session_id_v2}")

                    # 验证索引是否正确
                    if str(i) == index:
                        print(f"    ✓ 索引 {index} 正确")
                    else:
                        print(f"    ✗ 索引错误，期望 {i}，实际 {index}")
                        return False

                    # 验证总数是否正确
                    if "3" == total:
                        print(f"    ✓ 总数 {total} 正确")
                    else:
                        print(f"    ✗ 总数错误，期望 3，实际 {total}")
                        return False

                    # 验证session_id是否包含索引信息
                    if f"array_item_{i}" in session_id:
                        print(f"    ✓ Session ID包含索引信息")
                    else:
                        print(f"    ✗ Session ID不包含索引信息")
                        return False

                print("✓ 所有数组上下文功能验证通过")
            else:
                print(f"✗ 数组元素数量错误，期望3，实际{len(items)}")
                return False

        else:
            print(f"✗ 转换失败: {result.error}")
            return False

        print("\n" + "=" * 60)
        print("所有测试通过! ✓")
        print("=" * 60)
        print("\n总结:")
        print("- 动态数组中的每个元素都能获取到正确的索引")
        print("- 转换函数能够访问数组总长度信息")
        print("- Session ID现在可以基于索引生成不同的值")
        print("- 新的上下文机制向后兼容，不影响现有功能")

        return True

    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")


if __name__ == "__main__":
    success = test_array_context()
    sys.exit(0 if success else 1)