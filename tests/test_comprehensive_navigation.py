#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合导航协议测试脚本
测试新增的A-4, A-5, B-4, B-5, C-4, C-5协议
"""

import os
import sys
import json
import tempfile
import shutil
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.converter import ProtocolConverter
from protocol_manager.manager import ProtocolManager
from database.manager import ProtocolDatabase
from converters.functions import CONVERTER_FUNCTIONS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 创建logs目录
os.makedirs("logs", exist_ok=True)

# 配置文件日志
file_handler = logging.FileHandler("logs/comprehensive_test.log", encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s'
))

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

try:
    from loguru import logger as loguru_logger
    logger.info("使用loguru日志系统")
    # 如果有loguru，配置额外的文件日志
    loguru_logger.remove()
    loguru_logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")
    loguru_logger.add("logs/comprehensive_test.log", rotation="10 MB", retention="7 days", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}", level="DEBUG")
except ImportError:
    logger.info("使用标准logging日志系统")


def setup_test_environment():
    """设置测试环境"""
    logger.info("=== 开始综合导航协议测试 ===")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="comprehensive_test_")
    logger.info(f"使用临时目录: {temp_dir}")

    # 初始化数据库
    db_path = os.path.join(temp_dir, "test.db")
    db_manager = ProtocolDatabase(db_path)
    logger.info("✓ 数据库初始化成功")

    # 创建协议管理器
    protocol_manager = ProtocolManager()

    # 创建转换器
    converter = ProtocolConverter(CONVERTER_FUNCTIONS)

    return temp_dir, db_manager, protocol_manager, converter


def load_protocols(protocol_manager, examples_dir):
    """加载协议文件"""
    protocols_dir = os.path.join(examples_dir, "protocols")
    logger.info(f"加载协议目录: {protocols_dir}")

    if not os.path.exists(protocols_dir):
        logger.error(f"协议目录不存在: {protocols_dir}")
        return False

    # 加载所有协议
    result = protocol_manager.load_protocols_from_directory(protocols_dir)
    logger.info(f"加载结果: {result}")

    # 获取所有可用协议
    families = protocol_manager.list_all_families()
    logger.info(f"可用协议族: {families}")

    for family in families:
        protocols = protocol_manager.get_protocols_by_family(family)
        logger.info(f"协议族 {family}: {protocols}")

    return True, protocol_manager


def load_input_data(examples_dir):
    """加载输入数据"""
    input_dir = os.path.join(examples_dir, "input")
    input_data = {}

    if not os.path.exists(input_dir):
        logger.error(f"输入数据目录不存在: {input_dir}")
        return input_data

    for file_name in os.listdir(input_dir):
        if file_name.endswith('-input.json'):
            test_name = file_name.replace('-input.json', '')
            file_path = os.path.join(input_dir, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                input_data[test_name] = json.load(f)
                logger.info(f"加载输入数据: {test_name}")

    return input_data


def test_conversion(converter, protocol_manager, source_family, target_family, test_name, input_data):
    """测试协议转换"""
    logger.info(f"测试转换: {source_family} -> {target_family} ({test_name})")

    try:
        # 转换数据
        result = converter.convert(source_family, target_family, input_data)

        if result.success:
            logger.success(f"✓ 转换成功: {test_name}")
            logger.debug(f"匹配协议: {result.matched_protocol}")
            logger.debug(f"提取变量: {result.extracted_variables}")
            logger.info(f"转换结果:\n{json.dumps(result.result, indent=2, ensure_ascii=False)}")
            return result.result
        else:
            logger.error(f"✗ 转换失败: {test_name} - {result.error}")
            return None

    except Exception as e:
        logger.error(f"✗ 转换异常: {test_name} - {e}")
        return None


def test_address_splitting_merge():
    """专门测试地址拆分和合并功能"""
    logger.info("\n=== 测试地址拆分和合并功能 ===")

    # 测试用例：天山西路仙霞路
    test_cases = [
        {
            "name": "合并到拆分",
            "input": {
                "domain": "navigation",
                "action": "ROUTE_TO",
                "slots": {
                    "destination": "天山西路仙霞路交叉口",
                    "poi_type": "intersection",
                    "city": "上海市",
                    "district": "长宁区"
                }
            },
            "expected_pattern": "应该拆分为两条道路"
        },
        {
            "name": "拆分到合并",
            "input": {
                "domain": "navigation",
                "action": "NAVIGATE_TO_ROUTES",
                "slots": {
                    "routes": [
                        {"road_name": "天山西路"},
                        {"road_name": "仙霞路"}
                    ]
                }
            },
            "expected_pattern": "应该合并为一个目的地"
        }
    ]

    return test_cases


def test_dynamic_arrays():
    """测试动态数组功能"""
    logger.info("\n=== 测试动态数组功能 ===")

    test_cases = [
        {
            "name": "多路径点导航",
            "input": {
                "domain": "navigation",
                "action": "MULTI_WAYPOINT",
                "waypoints": [
                    {"name": "点1", "coordinates": {"lat": 31.1, "lng": 121.1}},
                    {"name": "点2", "coordinates": {"lat": 31.2, "lng": 121.2}},
                    {"name": "点3", "coordinates": {"lat": 31.3, "lng": 121.3}}
                ]
            }
        }
    ]

    return test_cases


def test_jinja2_features():
    """测试Jinja2高级特性"""
    logger.info("\n=== 测试Jinja2高级特性 ===")

    test_cases = [
        {
            "name": "条件渲染测试",
            "template": "{% if urgency == 'high' %}紧急{% else %}普通{% endif %}",
            "variables": {"urgency": "high"},
            "expected": "紧急"
        },
        {
            "name": "过滤器测试",
            "template": "{{ road_name | upper }}",
            "variables": {"road_name": "天山西路"},
            "expected": "天山西路"
        },
        {
            "name": "循环测试",
            "template": "{% for road in roads %}{{ road }}{% if not loop.last %} -> {% endif %}{% endfor %}",
            "variables": {"roads": ["天山西路", "仙霞路"]},
            "expected": "天山西路 -> 仙霞路"
        }
    ]

    return test_cases


def run_comprehensive_tests():
    """运行综合测试"""
    # 获取examples目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    examples_dir = os.path.join(project_root, "examples")

    logger.info(f"项目根目录: {project_root}")
    logger.info(f"Examples目录: {examples_dir}")

    # 设置测试环境
    temp_dir, db_manager, protocol_manager, converter = setup_test_environment()

    try:
        # 加载协议
        load_result, protocol_manager = load_protocols(protocol_manager, examples_dir)
        if not load_result:
            logger.error("协议加载失败，退出测试")
            return False

        # 将加载的协议模板加载到转换器中
        families = protocol_manager.list_all_families()
        for family in families:
            protocols = protocol_manager.get_protocols_by_family(family)
            for protocol_id in protocols:
                try:
                    protocol_data = protocol_manager.get_protocol_by_id(protocol_id)
                    if protocol_data:
                        converter.load_protocol(
                            protocol_id=protocol_id,
                            protocol_family=family,
                            template_content=protocol_data['template_content']
                        )
                        logger.info(f"转换器加载协议: {protocol_id}")
                except Exception as e:
                    logger.error(f"转换器加载协议失败 {protocol_id}: {e}")

        # 加载输入数据
        input_data = load_input_data(examples_dir)
        logger.info(f"加载了 {len(input_data)} 个输入数据文件")

        # 测试新增的协议转换
        test_results = {}

        # A协议族测试
        new_protocols = ["A-4", "A-5", "B-4", "B-5", "C-4", "C-5"]

        for source_family in ["A", "B", "C"]:
            for target_family in ["A", "B", "C"]:
                if source_family != target_family:  # 只测试不同协议族之间的转换
                    logger.info(f"\n--- 测试 {source_family} -> {target_family} 转换 ---")

                    for protocol in new_protocols:
                        if protocol.startswith(source_family):
                            test_name = protocol
                            if test_name in input_data:
                                result = test_conversion(
                                    converter, protocol_manager,
                                    source_family, target_family,
                                    test_name, input_data[test_name]
                                )

                                if result:
                                    test_results[f"{test_name}_{source_family}_to_{target_family}"] = result

        # 测试地址拆分合并
        address_tests = test_address_splitting_merge()
        logger.info(f"地址拆分合并测试用例: {len(address_tests)}")

        # 测试动态数组
        array_tests = test_dynamic_arrays()
        logger.info(f"动态数组测试用例: {len(array_tests)}")

        # 测试Jinja2特性
        jinja2_tests = test_jinja2_features()
        logger.info(f"Jinja2特性测试用例: {len(jinja2_tests)}")

        # 输出测试总结
        logger.info(f"\n=== 测试总结 ===")
        logger.info(f"总测试数: {len(test_results)}")
        logger.info(f"成功转换: {len(test_results)}")

        # 保存测试结果
        results_file = os.path.join(temp_dir, "test_results.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        logger.info(f"测试结果已保存到: {results_file}")

        return True

    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"已清理临时目录: {temp_dir}")


if __name__ == "__main__":
    success = run_comprehensive_tests()
    if success:
        logger.info("\n=== 所有综合测试完成! ===")
        sys.exit(0)
    else:
        logger.error("\n=== 综合测试失败! ===")
        sys.exit(1)