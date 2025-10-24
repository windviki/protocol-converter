#!/usr/bin/env python3
"""
Protocol Converter CLI - 命令行界面
"""

import argparse
import json
import sys
import os
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.loader import ProtocolLoader
from core.converter import ProtocolConverter
from converters.functions import CONVERTER_FUNCTIONS
from protocol_manager.manager import ProtocolManager
from database.connection import init_database


def setup_argument_parser() -> argparse.ArgumentParser:
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='Protocol Converter - 通用协议转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 初始化数据库
  python cli.py init-db
  
  # 加载协议文件
  python cli.py load -d ./protocols
  
  # 转换协议
  python cli.py convert -s A -t C -i input.json -o output.json
  
  # 列出所有协议族
  python cli.py list-families
  
  # 列出指定协议族的所有协议
  python cli.py list-protocols -f A
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 初始化数据库命令
    init_parser = subparsers.add_parser('init-db', help='初始化数据库')
    
    # 加载协议命令
    load_parser = subparsers.add_parser('load', help='加载协议文件')
    load_parser.add_argument('-d', '--directory', required=True, help='协议文件目录')
    load_parser.add_argument('--db-path', default='protocols.db', help='数据库文件路径')
    
    # 转换协议命令
    convert_parser = subparsers.add_parser('convert', help='转换协议')
    convert_parser.add_argument('-s', '--source', required=True, help='源协议族')
    convert_parser.add_argument('-t', '--target', required=True, help='目标协议族')
    convert_parser.add_argument('-i', '--input', required=True, help='输入JSON文件')
    convert_parser.add_argument('-o', '--output', help='输出JSON文件（可选，默认输出到控制台）')
    convert_parser.add_argument('--db-path', default='protocols.db', help='数据库文件路径')
    
    # 列出协议族命令
    list_families_parser = subparsers.add_parser('list-families', help='列出所有协议族')
    list_families_parser.add_argument('--db-path', default='protocols.db', help='数据库文件路径')
    
    # 列出协议命令
    list_protocols_parser = subparsers.add_parser('list-protocols', help='列出指定协议族的所有协议')
    list_protocols_parser.add_argument('-f', '--family', required=True, help='协议族名称')
    list_protocols_parser.add_argument('--db-path', default='protocols.db', help='数据库文件路径')
    
    # 显示协议详情命令
    show_parser = subparsers.add_parser('show', help='显示协议详情')
    show_parser.add_argument('protocol_id', help='协议ID')
    show_parser.add_argument('--db-path', default='protocols.db', help='数据库文件路径')
    
    return parser


def cmd_init_db(args):
    """初始化数据库命令"""
    print("正在初始化数据库...")
    try:
        init_database()
        print("✓ 数据库初始化成功")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        sys.exit(1)


def cmd_load(args):
    """加载协议文件命令"""
    print(f"正在从目录加载协议文件: {args.directory}")
    
    if not os.path.exists(args.directory):
        print(f"✗ 目录不存在: {args.directory}")
        sys.exit(1)
    
    try:
        # 使用ProtocolManager加载协议
        manager = ProtocolManager()
        result = manager.load_protocols_from_directory(args.directory)
        
        print(f"\n加载完成:")
        print(f"  总文件数: {result['total_files']}")
        print(f"  成功加载: {result['loaded_files']}")
        print(f"  加载失败: {result['failed_files']}")
        
        if result['errors']:
            print(f"\n错误详情:")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result['loaded_files'] > 0:
            print(f"\n✓ 协议加载成功")
        else:
            print(f"\n✗ 没有成功加载任何协议文件")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ 加载协议文件失败: {e}")
        sys.exit(1)


def cmd_convert(args):
    """转换协议命令"""
    print(f"正在转换协议: {args.source} -> {args.target}")
    
    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"✗ 输入文件不存在: {args.input}")
        sys.exit(1)
    
    try:
        # 读取输入JSON
        with open(args.input, 'r', encoding='utf-8') as f:
            source_json = json.load(f)
        
        print(f"输入JSON: {json.dumps(source_json, ensure_ascii=False, indent=2)}")
        
        # 创建转换器
        converter = ProtocolConverter(CONVERTER_FUNCTIONS)
        
        # 从数据库加载协议
        manager = ProtocolManager()
        
        # 获取源协议族的所有协议
        source_protocols = manager.get_protocols_by_family(args.source)
        if not source_protocols:
            print(f"✗ 未找到协议族 '{args.source}' 的任何协议")
            sys.exit(1)
        
        # 加载所有协议到转换器
        for protocol_id in source_protocols:
            protocol_info = manager.get_protocol_by_id(protocol_id)
            if protocol_info:
                converter.load_protocol(
                    protocol_id=protocol_id,
                    protocol_family=protocol_info['family'],
                    template_content=protocol_info['template']
                )
        
        # 获取目标协议族的所有协议
        target_protocols = manager.get_protocols_by_family(args.target)
        for protocol_id in target_protocols:
            protocol_info = manager.get_protocol_by_id(protocol_id)
            if protocol_info:
                converter.load_protocol(
                    protocol_id=protocol_id,
                    protocol_family=protocol_info['family'],
                    template_content=protocol_info['template']
                )
        
        # 执行转换
        result = converter.convert(args.source, args.target, source_json)
        
        if result.success:
            print(f"\n✓ 转换成功")
            print(f"匹配的协议: {result.matched_protocol}")
            print(f"提取的变量: {result.variables}")
            print(f"\n转换结果:")
            output_json = json.dumps(result.result, ensure_ascii=False, indent=2)
            print(output_json)
            
            # 如果指定了输出文件，保存结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_json)
                print(f"\n结果已保存到: {args.output}")
        else:
            print(f"\n✗ 转换失败: {result.error}")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ 转换失败: {e}")
        sys.exit(1)


def cmd_list_families(args):
    """列出协议族命令"""
    try:
        manager = ProtocolManager()
        families = manager.list_all_families()
        
        if families:
            print("可用协议族:")
            for family in sorted(families):
                print(f"  - {family}")
        else:
            print("没有找到任何协议族")
            
    except Exception as e:
        print(f"✗ 获取协议族列表失败: {e}")
        sys.exit(1)


def cmd_list_protocols(args):
    """列出协议命令"""
    try:
        manager = ProtocolManager()
        protocols = manager.get_protocols_by_family(args.family)
        
        if protocols:
            print(f"协议族 '{args.family}' 的协议:")
            for protocol in sorted(protocols):
                print(f"  - {protocol}")
        else:
            print(f"协议族 '{args.family}' 没有找到任何协议")
            
    except Exception as e:
        print(f"✗ 获取协议列表失败: {e}")
        sys.exit(1)


def cmd_show(args):
    """显示协议详情命令"""
    try:
        manager = ProtocolManager()
        protocol_info = manager.get_protocol_by_id(args.protocol_id)
        
        if protocol_info:
            print(f"协议详情: {args.protocol_id}")
            print(f"协议族: {protocol_info['family']}")
            print(f"普通变量: {protocol_info['normal_vars']}")
            print(f"特殊变量: {protocol_info['special_vars']}")
            print(f"\n模板内容:")
            print(json.dumps(protocol_info['template'], ensure_ascii=False, indent=2))
            print(f"\nSchema结构:")
            print(json.dumps(protocol_info['schema'], ensure_ascii=False, indent=2))
        else:
            print(f"✗ 未找到协议: {args.protocol_id}")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ 获取协议详情失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 执行对应命令
    if args.command == 'init-db':
        cmd_init_db(args)
    elif args.command == 'load':
        cmd_load(args)
    elif args.command == 'convert':
        cmd_convert(args)
    elif args.command == 'list-families':
        cmd_list_families(args)
    elif args.command == 'list-protocols':
        cmd_list_protocols(args)
    elif args.command == 'show':
        cmd_show(args)
    else:
        print(f"未知命令: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()