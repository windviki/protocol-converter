#!/usr/bin/env python3
"""
YAML协议转换系统完整测试套件
支持所有协议族和输入文件的全面测试
"""

import sys
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from protocols.yaml_loader import create_yaml_loader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YAMLSystemTester:
    """YAML系统完整测试器"""

    def __init__(self):
        self.test_results = []
        self.loader = None
        self.examples_dir = Path(__file__).parent.parent / "examples"
        self.input_dir = self.examples_dir / "input"
        self.protocols_dir = self.examples_dir / "protocols"

    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 YAML协议转换系统完整测试套件")
        print("=" * 80)

        tests = [
            ("YAML加载器基础测试", self.test_yaml_loader),
            ("协议族映射测试", self.test_protocol_family_mapping),
            ("全面协议转换测试", self.test_comprehensive_protocol_conversion),
            ("输入文件对比验证", self.test_input_file_comparison),
            ("边界条件测试", self.test_edge_cases),
            ("性能测试", self.test_performance),
            ("协议覆盖度测试", self.test_protocol_coverage)
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}")
            print("-" * 60)
            try:
                result = test_func()
                if result:
                    print(f"✅ {test_name} 通过")
                    passed += 1
                    self.test_results.append((test_name, "PASS", None))
                else:
                    print(f"❌ {test_name} 失败")
                    self.test_results.append((test_name, "FAIL", "测试返回False"))
            except Exception as e:
                print(f"💥 {test_name} 异常: {e}")
                logger.exception(f"Test {test_name} failed")
                self.test_results.append((test_name, "ERROR", str(e)))

        # 输出测试总结
        print(f"\n📊 测试总结")
        print("=" * 80)
        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"成功率: {passed/total*100:.1f}%")

        # 输出详细结果
        print(f"\n📋 详细测试结果:")
        for test_name, status, error in self.test_results:
            status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "💥"
            print(f"  {status_icon} {test_name}: {status}")
            if error:
                print(f"    错误: {error}")

        if passed == total:
            print("\n🎉 所有测试通过！YAML协议转换系统工作完美！")
            return True
        else:
            print(f"\n⚠️ 存在 {total - passed} 个失败的测试，需要修复")
            return False

    def test_yaml_loader(self):
        """测试YAML加载器"""
        self.loader = create_yaml_loader()
        loaded_count = self.loader.load_from_directory()

        if loaded_count == 0:
            print("❌ 没有加载任何协议")
            return False

        print(f"✅ 成功加载 {loaded_count} 个YAML协议")

        # 检查基本协议
        basic_protocols = ["A-1", "B-1", "C-1"]
        for protocol_id in basic_protocols:
            template = self.loader.get_template(protocol_id)
            if not template:
                print(f"❌ 未找到{protocol_id}协议")
                return False
            if len(template.variable_mapping.regular_variables) == 0:
                print(f"❌ {protocol_id}协议没有变量")
                return False
            print(f"  ✅ {protocol_id}: {len(template.variable_mapping.regular_variables)}个变量")

        return True

    def test_protocol_family_mapping(self):
        """测试协议族映射"""
        if not self.loader:
            return False

        # 读取所有输入文件，建立协议族映射
        input_files = list(self.input_dir.glob("*.json"))
        if not input_files:
            print("❌ 没有找到输入文件")
            return False

        protocol_families = {}
        for input_file in input_files:
            # 解析文件名获取协议信息
            stem = input_file.stem  # 如 "A-1-input"
            parts = stem.split('-')
            if len(parts) >= 2:
                family = parts[0]
                protocol_num = parts[1]
                if family not in protocol_families:
                    protocol_families[family] = []
                protocol_families[family].append(protocol_num)

        print(f"✅ 发现协议族: {list(protocol_families.keys())}")
        for family, protocols in protocol_families.items():
            print(f"  {family}族: {len(protocols)}个协议 ({', '.join(protocols)})")

        self.protocol_families = protocol_families
        return True

    def test_comprehensive_protocol_conversion(self):
        """测试全面协议转换"""
        if not self.loader:
            return False

        converter = self.loader.get_converter()
        conversion_results = []
        total_conversions = 0
        successful_conversions = 0

        # 获取所有输入文件
        input_files = list(self.input_dir.glob("*.json"))

        for input_file in input_files:
            try:
                # 解析协议信息
                stem = input_file.stem  # 如 "A-1-input"
                parts = stem.split('-')
                if len(parts) < 2:
                    continue

                source_family = parts[0]
                source_protocol = f"{source_family}-{parts[1]}"

                # 读取输入数据
                with open(input_file, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)

                print(f"\n📝 测试 {source_protocol} 转换:")
                print(f"  输入文件: {input_file.name}")
                print(f"  输入数据: {json.dumps(input_data, ensure_ascii=False)}")

                # 测试转换到所有其他协议族
                for target_family in ['A', 'B', 'C']:
                    if target_family == source_family:
                        continue  # 跳过相同协议族

                    total_conversions += 1

                    try:
                        result = converter.convert(source_family, target_family, input_data)

                        if result.success:
                            successful_conversions += 1
                            print(f"  ✅ {source_family}→{target_family}: 成功")
                            conversion_results.append({
                                'source': source_protocol,
                                'source_family': source_family,
                                'target_family': target_family,
                                'success': True,
                                'result': result.result,
                                'matched_protocol': result.matched_protocol
                            })
                        else:
                            print(f"  ❌ {source_family}→{target_family}: 失败 - {result.error}")
                            conversion_results.append({
                                'source': source_protocol,
                                'source_family': source_family,
                                'target_family': target_family,
                                'success': False,
                                'error': result.error
                            })

                    except Exception as e:
                        print(f"  💥 {source_family}→{target_family}: 异常 - {e}")
                        conversion_results.append({
                            'source': source_protocol,
                            'source_family': source_family,
                            'target_family': target_family,
                            'success': False,
                            'error': str(e)
                        })

            except Exception as e:
                print(f"❌ 处理文件 {input_file.name} 时出错: {e}")
                continue

        self.conversion_results = conversion_results

        print(f"\n📊 转换统计:")
        print(f"  总转换数: {total_conversions}")
        print(f"  成功转换: {successful_conversions}")
        print(f"  成功率: {successful_conversions/total_conversions*100:.1f}%" if total_conversions > 0 else "  成功率: 0%")

        # 检查成功率
        if total_conversions == 0:
            print("❌ 没有执行任何转换")
            return False

        success_rate = successful_conversions / total_conversions
        if success_rate < 0.8:  # 期望至少80%成功率
            print(f"❌ 成功率过低: {success_rate*100:.1f}%")
            return False

        print(f"✅ 转换成功率达标: {success_rate*100:.1f}%")
        return True

    def test_input_file_comparison(self):
        """测试输入文件对比验证"""
        if not hasattr(self, 'conversion_results') or not self.conversion_results:
            print("❌ 没有转换结果可供对比")
            return False

        comparison_results = []
        matched_comparisons = 0
        total_comparisons = 0

        print(f"\n🔍 开始对比验证:")

        for result in self.conversion_results:
            if not result['success']:
                continue

            source_protocol = result['source']
            target_family = result['target_family']

            # 尝试找到对应的输入文件进行对比
            source_parts = source_protocol.split('-')
            if len(source_parts) < 2:
                continue

            protocol_num = source_parts[1]
            target_input_file = self.input_dir / f"{target_family}-{protocol_num}-input.json"

            total_comparisons += 1

            if target_input_file.exists():
                try:
                    # 读取目标输入文件
                    with open(target_input_file, 'r', encoding='utf-8') as f:
                        expected_data = json.load(f)

                    # 获取转换结果
                    actual_data = result['result']

                    # 进行深度对比
                    match_score = self._compare_json_structures(expected_data, actual_data)

                    print(f"  📊 {source_protocol} → {target_family}-{protocol_num}:")
                    print(f"    期望: {json.dumps(expected_data, ensure_ascii=False)}")
                    print(f"    实际: {json.dumps(actual_data, ensure_ascii=False)}")
                    print(f"    匹配度: {match_score*100:.1f}%")

                    if match_score >= 0.8:  # 80%以上认为匹配
                        matched_comparisons += 1
                        print(f"    ✅ 匹配成功")
                        comparison_results.append({
                            'source': source_protocol,
                            'target': f"{target_family}-{protocol_num}",
                            'match_score': match_score,
                            'matched': True
                        })
                    else:
                        print(f"    ❌ 匹配度过低")
                        comparison_results.append({
                            'source': source_protocol,
                            'target': f"{target_family}-{protocol_num}",
                            'match_score': match_score,
                            'matched': False
                        })

                except Exception as e:
                    print(f"  💥 对比 {target_input_file.name} 时出错: {e}")
                    comparison_results.append({
                        'source': source_protocol,
                        'target': f"{target_family}-{protocol_num}",
                        'match_score': 0,
                        'matched': False,
                        'error': str(e)
                    })
            else:
                print(f"  ⚠️  未找到目标文件: {target_input_file.name}")
                comparison_results.append({
                    'source': source_protocol,
                    'target': f"{target_family}-{protocol_num}",
                    'match_score': None,
                    'matched': False,
                    'reason': "目标文件不存在"
                })

        self.comparison_results = comparison_results

        print(f"\n📊 对比验证统计:")
        print(f"  总对比数: {total_comparisons}")
        print(f"  匹配成功: {matched_comparisons}")
        print(f"  匹配率: {matched_comparisons/total_comparisons*100:.1f}%" if total_comparisons > 0 else "  匹配率: 0%")

        if total_comparisons == 0:
            print("❌ 没有执行任何对比")
            return False

        match_rate = matched_comparisons / total_comparisons
        if match_rate < 0.6:  # 期望至少60%匹配率
            print(f"❌ 匹配率过低: {match_rate*100:.1f}%")
            return False

        print(f"✅ 对比验证达标: {match_rate*100:.1f}%")
        return True

    def _compare_json_structures(self, expected: Dict, actual: Dict) -> float:
        """比较两个JSON结构的相似度"""
        def _compare_recursive(exp, act, path=""):
            if isinstance(exp, dict) and isinstance(act, dict):
                if not exp:
                    return 1.0

                total_score = 0
                total_items = 0

                for key in exp:
                    if key in act:
                        score = _compare_recursive(exp[key], act[key], f"{path}.{key}")
                        total_score += score
                        total_items += 1
                    else:
                        total_items += 1

                return total_score / total_items if total_items > 0 else 0

            elif isinstance(exp, list) and isinstance(act, list):
                if not exp:
                    return 1.0

                # 简单的列表比较：按顺序比较对应元素
                min_len = min(len(exp), len(act))
                if min_len == 0:
                    return 1.0

                total_score = sum(_compare_recursive(exp[i], act[i], f"{path}[{i}]") for i in range(min_len))
                # 长度差异影响分数
                length_factor = min_len / max(len(exp), len(act))
                return (total_score / min_len) * length_factor

            else:
                # 基本类型比较
                if exp == act:
                    return 1.0
                else:
                    # 部分匹配：字符串相似度
                    if isinstance(exp, str) and isinstance(act, str):
                        # 简单的字符串相似度
                        common_chars = set(exp.lower()) & set(act.lower())
                        total_chars = set(exp.lower()) | set(act.lower())
                        return len(common_chars) / len(total_chars) if total_chars else 0
                    return 0.0

        try:
            return _compare_recursive(expected, actual)
        except Exception:
            return 0.0

    def test_edge_cases(self):
        """测试边界条件"""
        if not self.loader:
            return False

        converter = self.loader.get_converter()

        # 测试用例
        edge_cases = [
            ("空输入", {}),
            ("只有domain", {"domain": "telephone"}),
            ("无效domain", {"domain": "invalid", "action": "TEST"}),
            ("空slots", {"domain": "telephone", "action": "DIAL", "slots": {}}),
            ("深层嵌套", {"domain": "telephone", "action": "DIAL", "slots": {"nested": {"deep": {"value": "test"}}}}),
        ]

        for case_name, test_data in edge_cases:
            try:
                result = converter.convert("A", "B", test_data)
                if result.success:
                    print(f"  ✅ {case_name}: 转换成功")
                else:
                    print(f"  ⚠️  {case_name}: 转换失败但未崩溃 - {result.error}")
            except Exception as e:
                print(f"  💥 {case_name}: 导致异常 - {e}")
                return False

        print("✅ 边界条件测试通过")
        return True

    def test_performance(self):
        """测试性能"""
        if not self.loader:
            return False

        import time
        converter = self.loader.get_converter()

        # 使用一个标准输入进行性能测试
        test_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        # 预热
        for _ in range(3):
            converter.convert("A", "B", test_input)

        # 性能测试
        start_time = time.time()
        iterations = 50
        successful_iterations = 0

        for i in range(iterations):
            try:
                result = converter.convert("A", "B", test_input)
                if result.success:
                    successful_iterations += 1
            except Exception:
                pass

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        success_rate = successful_iterations / iterations

        print(f"  性能测试结果:")
        print(f"    迭代次数: {iterations}")
        print(f"    成功次数: {successful_iterations}")
        print(f"    成功率: {success_rate*100:.1f}%")
        print(f"    总时间: {total_time:.3f}s")
        print(f"    平均时间: {avg_time*1000:.2f}ms")

        # 性能要求：平均时间小于100ms，成功率大于95%
        if avg_time > 0.1:  # 100ms
            print("❌ 平均转换时间过长")
            return False

        if success_rate < 0.95:  # 95%
            print("❌ 成功率过低")
            return False

        print("✅ 性能测试通过")
        return True

    def test_protocol_coverage(self):
        """测试协议覆盖度"""
        if not self.loader:
            return False

        loaded_protocols = self.loader.get_loaded_protocols()
        protocol_families = set()

        for protocol_id in loaded_protocols:
            template = self.loader.get_template(protocol_id)
            if template:
                protocol_families.add(template.family)

        expected_families = {'A', 'B', 'C'}

        print(f"  加载的协议: {len(loaded_protocols)}个")
        print(f"  协议族: {protocol_families}")

        if not expected_families.issubset(protocol_families):
            missing = expected_families - protocol_families
            print(f"❌ 缺少协议族: {missing}")
            return False

        # 检查每个协议族至少有一个协议
        for family in expected_families:
            family_protocols = [p for p in loaded_protocols if p.startswith(f"{family}-")]
            if len(family_protocols) == 0:
                print(f"❌ {family}族没有协议")
                return False
            print(f"  ✅ {family}族: {len(family_protocols)}个协议")

        print("✅ 协议覆盖度测试通过")
        return True

def main():
    """主函数"""
    tester = YAMLSystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()