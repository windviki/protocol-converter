#!/usr/bin/env python3
"""
协议转换器使用示例
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol_converter.database.connection import init_database
from protocol_converter.protocol_manager.manager import ProtocolManager
from protocol_converter.core.converter import ProtocolConverter
from protocol_converter.converters.functions import CONVERTER_FUNCTIONS


def main():
    """主函数"""
    print("协议转换器使用示例")
    print("=" * 40)
    
    # 1. 初始化数据库
    print("1. 初始化数据库...")
    try:
        init_database()
        print("✓ 数据库初始化成功")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return
    
    # 2. 加载示例协议
    print("\n2. 加载示例协议...")
    try:
        manager = ProtocolManager()
        examples_dir = os.path.join(os.path.dirname(__file__), "examples", "protocols")
        
        if not os.path.exists(examples_dir):
            print(f"✗ 示例协议目录不存在: {examples_dir}")
            print("请确保 examples/protocols 目录存在并包含协议文件")
            return
        
        result = manager.load_protocols_from_directory(examples_dir)
        print(f"✓ 加载完成: {result['loaded_files']} 个协议")
        
    except Exception as e:
        print(f"✗ 加载协议失败: {e}")
        return
    
    # 3. 显示协议族信息
    print("\n3. 协议族信息...")
    try:
        families = manager.list_all_families()
        print(f"可用协议族: {families}")
        
        for family in families:
            protocols = manager.get_protocols_by_family(family)
            print(f"  {family}: {protocols}")
    except Exception as e:
        print(f"✗ 获取协议族信息失败: {e}")
        return
    
    # 4. 创建转换器
    print("\n4. 创建转换器...")
    try:
        converter = ProtocolConverter(CONVERTER_FUNCTIONS)
        
        # 加载所有协议到转换器
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
        
        print("✓ 转换器创建成功")
    except Exception as e:
        print(f"✗ 创建转换器失败: {e}")
        return
    
    # 5. 执行转换示例
    print("\n5. 转换示例...")
    
    # 示例1: A -> C 转换
    print("\n示例1: A协议 -> C协议")
    print("-" * 30)
    
    input_data = {
        "domain": "telephone",
        "action": "DIAL",
        "slots": {
            "category": "手机",
            "name": "张三",
            "raw_name": "张三"
        }
    }
    
    print(f"输入数据:")
    print(json.dumps(input_data, ensure_ascii=False, indent=2))
    
    try:
        result = converter.convert("A", "C", input_data)
        
        if result.success:
            print(f"\n转换结果:")
            print(json.dumps(result.result, ensure_ascii=False, indent=2))
            print(f"\n匹配协议: {result.matched_protocol}")
            print(f"提取变量: {result.variables}")
        else:
            print(f"✗ 转换失败: {result.error}")
    except Exception as e:
        print(f"✗ 转换过程出错: {e}")
    
    # 示例2: A -> B 转换
    print("\n示例2: A协议 -> B协议")
    print("-" * 30)
    
    input_data2 = {
        "domain": "telephone",
        "action": "ANSWER",
        "slots": {
            "category": "座机",
            "name": "李四",
            "duration": "120"
        }
    }
    
    print(f"输入数据:")
    print(json.dumps(input_data2, ensure_ascii=False, indent=2))
    
    try:
        result2 = converter.convert("A", "B", input_data2)
        
        if result2.success:
            print(f"\n转换结果:")
            print(json.dumps(result2.result, ensure_ascii=False, indent=2))
            print(f"\n匹配协议: {result2.matched_protocol}")
            print(f"提取变量: {result2.variables}")
        else:
            print(f"✗ 转换失败: {result2.error}")
    except Exception as e:
        print(f"✗ 转换过程出错: {e}")
    
    # 6. 显示协议详情
    print("\n6. 协议详情示例...")
    try:
        protocol_info = manager.get_protocol_by_id("A-1")
        if protocol_info:
            print("A-1 协议详情:")
            print(f"协议族: {protocol_info['family']}")
            print(f"普通变量: {protocol_info['normal_vars']}")
            print(f"特殊变量: {protocol_info['special_vars']}")
            print(f"模板内容:")
            print(json.dumps(protocol_info['template'], ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"✗ 获取协议详情失败: {e}")
    
    print("\n" + "=" * 40)
    print("示例完成!")
    print("您可以使用 CLI 工具进行更多操作:")
    print("  python cli.py --help")
    print("=" * 40)


if __name__ == "__main__":
    main()