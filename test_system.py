#!/usr/bin/env python3
"""
协议转换器测试脚本
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


def test_protocol_conversion():
    """测试协议转换功能"""
    print("=" * 50)
    print("协议转换器测试")
    print("=" * 50)
    
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
        
        # 创建A协议
        a_protocol_dir = os.path.join(temp_dir, "A")
        os.makedirs(a_protocol_dir)
        
        a1_content = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "{{ phone_type }}",
                "name": "{{ person }}",
                "raw_name": "{{ person }}"
            }
        }
        
        with open(os.path.join(a_protocol_dir, "A-1.json"), "w", encoding="utf-8") as f:
            json.dump(a1_content, f, ensure_ascii=False, indent=2)
        
        # 创建C协议
        c_protocol_dir = os.path.join(temp_dir, "C")
        os.makedirs(c_protocol_dir)
        
        c1_content = {
            "tao": "phone.contact.call",
            "slots": [
                {
                    "name": "PERSON",
                    "value": "{{ person }}",
                    "label": "O"
                },
                {
                    "name": "PHONE_TYPE",
                    "value": "{{ phone_type }}",
                    "label": "{{ __sid }}"
                }
            ]
        }
        
        with open(os.path.join(c_protocol_dir, "C-1.json"), "w", encoding="utf-8") as f:
            json.dump(c1_content, f, ensure_ascii=False, indent=2)
        
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
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "手机",
                "name": "张三",
                "raw_name": "张三"
            }
        }
        
        print(f"输入数据: {json.dumps(test_input, ensure_ascii=False, indent=2)}")
        
        # 执行转换 A -> C
        print("\n转换 A -> C:")
        result = converter.convert("A", "C", test_input)
        
        if result.success:
            print("✓ 转换成功")
            print(f"匹配协议: {result.matched_protocol}")
            print(f"提取变量: {result.variables}")
            print(f"转换结果:")
            print(json.dumps(result.result, ensure_ascii=False, indent=2))
        else:
            print(f"✗ 转换失败: {result.error}")
            return False
        
        # 7. 验证结果
        print("\n7. 验证转换结果...")
        
        expected_result = {
            "tao": "phone.contact.call",
            "slots": [
                {
                    "name": "PERSON",
                    "value": "张三",
                    "label": "O"
                },
                {
                    "name": "PHONE_TYPE",
                    "value": "手机",
                    "label": "PHONE_TYPE_MOBILE"
                }
            ]
        }
        
        if result.result == expected_result:
            print("✓ 转换结果正确")
        else:
            print("✗ 转换结果不正确")
            print(f"期望结果: {json.dumps(expected_result, ensure_ascii=False, indent=2)}")
            return False
        
        print("\n" + "=" * 50)
        print("所有测试通过! ✓")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"已清理临时目录: {temp_dir}")


if __name__ == "__main__":
    success = test_protocol_conversion()
    sys.exit(0 if success else 1)