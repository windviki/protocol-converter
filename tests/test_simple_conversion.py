#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的协议转换测试
直接使用现有工作的系统进行测试
"""

import os
import sys
import logging
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

from core.converter import ProtocolConverter
from converters.functions import CONVERTER_FUNCTIONS


def test_basic_conversion():
    """测试基础转换功能"""
    logger.info("=== 开始基础转换测试 ===")

    try:
        # 创建转换器
        converter = ProtocolConverter(CONVERTER_FUNCTIONS)
        logger.info("✓ 转换器创建成功")

        # 测试数据
        test_data = {
            "domain": "navigation",
            "action": "ROUTE_TO",
            "slots": {
                "destination": "天山西路仙霞路交叉口",
                "poi_type": "intersection",
                "vehicle_type": "car",
                "urgency": "normal",
                "route_type": "fastest",
                "coordinates": {
                    "latitude": "31.2204",
                    "longitude": "121.4256"
                }
            }
        }

        # 手动加载一些协议模板进行测试
        # A-4 协议（车载导航）
        a4_template = {
            "domain": "navigation",
            "action": "ROUTE_TO",
            "slots": {
                "destination": "{{ destination }}",
                "poi_type": "{{ poi_type }}",
                "vehicle_type": "{{ vehicle_type }}",
                "urgency": "{{ urgency }}",
                "route_type": "{{ route_type }}",
                "coordinates": {
                    "latitude": "{{ latitude }}",
                    "longitude": "{{ longitude }}",
                    "address": "{{ full_address }}"
                }
            }
        }

        # C-4 协议（C协议族格式）
        c4_template = {
            "tao": "navigation.route.to_intersection",
            "slots": [
                {
                    "name": "PRIMARY_ROAD",
                    "value": "{{ func_primary_road() }}",
                    "label": "{{ __sid }}",
                    "metadata": {
                        "type": "road",
                        "importance": "high",
                        "source_field": "primary_road"
                    }
                },
                {
                    "name": "SECONDARY_ROAD",
                    "value": "{{ func_secondary_road() }}",
                    "label": "{{ __sid }}",
                    "metadata": {
                        "type": "road",
                        "importance": "medium",
                        "source_field": "secondary_road"
                    }
                },
                {
                    "name": "LOCATION",
                    "value": {
                        "city": "{{ city | default '上海' }}",
                        "district": "{{ district | default '长宁区' }}",
                        "coordinates": {
                            "lat": "{{ latitude }}",
                            "lng": "{{ longitude }}"
                        }
                    },
                    "label": "{{ __sid }}",
                    "metadata": {
                        "type": "location",
                        "importance": "high",
                        "is_nested": "true"
                    }
                }
            ]
        }

        # 加载协议
        converter.load_protocol("A-4", "A", a4_template)
        converter.load_protocol("C-4", "C", c4_template)
        logger.info("✓ 协议加载成功")

        # 测试 A -> C 转换
        logger.info("测试 A -> C 转换...")
        result = converter.convert("A", "C", test_data)

        if result.success:
            logger.info("✓ A -> C 转换成功")
            logger.info(f"匹配协议: {result.matched_protocol}")
            logger.info(f"提取变量: {result.variables}")
            logger.info("转换结果:")
            logger.info(json.dumps(result.result, indent=2, ensure_ascii=False))
            return True
        else:
            logger.error(f"✗ A -> C 转换失败: {result.error}")
            return False

    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_jinja2_preprocessing():
    """测试Jinja2预处理功能"""
    logger.info("=== 测试Jinja2预处理功能 ===")

    try:
        from utils.json_utils import preprocess_json_content

        # 测试复杂的Jinja2语法
        test_content = '''{
            "name": "{{ poi_type | default 'unknown' }}",
            "condition": "{% if urgency == 'high' %}urgent{% else %}normal{% endif %}",
            "array": [
                "{# array_dynamic: true #}",
                {
                    "road": "{{ road_name | upper }}",
                    "distance": "{{ distance | default 'unknown' }}"
                }
            ]
        }'''

        logger.info("原始内容:")
        logger.info(test_content)

        processed = preprocess_json_content(test_content)
        logger.info("预处理后内容:")
        logger.info(processed)

        # 尝试解析
        import json
        parsed = json.loads(processed)
        logger.info("✓ JSON解析成功")
        logger.info(f"解析结果: {json.dumps(parsed, indent=2, ensure_ascii=False)}")
        return True

    except Exception as e:
        logger.error(f"✗ Jinja2预处理测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行所有测试...")

    tests = [
        ("Jinja2预处理功能", test_jinja2_preprocessing),
        ("基础转换功能", test_basic_conversion),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"运行测试: {test_name}")
        logger.info(f"{'='*50}")

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"测试异常: {test_name} - {e}")
            results.append((test_name, False))

    # 输出测试总结
    logger.info(f"\n{'='*50}")
    logger.info("测试总结")
    logger.info(f"{'='*50}")

    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{test_name}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    logger.info(f"\n总计: {passed}/{total} 个测试通过")

    if passed == total:
        logger.info("🎉 所有测试都通过了！")
    else:
        logger.warning(f"⚠️  {total - passed} 个测试失败")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)