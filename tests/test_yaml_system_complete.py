#!/usr/bin/env python3
"""
YAML协议转换系统完整测试套件
"""

import sys
import json
import logging
from pathlib import Path

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

    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 YAML协议转换系统完整测试套件")
        print("=" * 60)

        tests = [
            ("YAML加载器测试", self.test_yaml_loader),
            ("协议匹配测试", self.test_protocol_matching),
            ("变量提取测试", self.test_variable_extraction),
            ("协议转换测试", self.test_protocol_conversion),
            ("跨协议族转换测试", self.test_cross_family_conversion),
            ("边界条件测试", self.test_edge_cases),
            ("性能测试", self.test_performance)
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}")
            print("-" * 40)
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
                self.test_results.append((test_name, "ERROR", str(e)))

        # 输出测试总结
        print(f"\n📊 测试总结")
        print("=" * 60)
        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"成功率: {passed/total*100:.1f}%")

        if passed == total:
            print("🎉 所有测试通过！YAML协议转换系统工作完美！")
            return True
        else:
            print("⚠️ 存在失败的测试，需要修复")
            return False

    def test_yaml_loader(self):
        """测试YAML加载器"""
        self.loader = create_yaml_loader()
        loaded_count = self.loader.load_from_directory()

        if loaded_count == 0:
            print("❌ 没有加载任何协议")
            return False

        print(f"✅ 成功加载 {loaded_count} 个YAML协议")

        # 检查A-1协议
        a1_template = self.loader.get_template("A-1")
        if not a1_template:
            print("❌ 未找到A-1协议")
            return False

        if len(a1_template.variable_mapping.regular_variables) == 0:
            print("❌ A-1协议没有变量")
            return False

        print(f"✅ A-1协议有 {len(a1_template.variable_mapping.regular_variables)} 个变量")
        return True

    def test_protocol_matching(self):
        """测试协议匹配"""
        if not self.loader:
            return False

        converter = self.loader.get_converter()
        matcher = converter.matcher

        # 测试电话拨号输入
        telephone_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        matched_protocol = matcher.match_protocol("A", telephone_input)
        if not matched_protocol:
            print("❌ 电话拨号输入没有匹配的协议")
            return False

        if matched_protocol != "A-1":
            print(f"❌ 匹配了错误的协议: {matched_protocol}")
            return False

        print(f"✅ 电话拨号输入正确匹配协议: {matched_protocol}")
        return True

    def test_variable_extraction(self):
        """测试变量提取"""
        if not self.loader:
            return False

        # 测试数据
        test_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        converter = self.loader.get_converter()
        matcher = converter.matcher
        extractor = converter.extractor

        # 获取A-1协议
        a1_protocol = matcher.protocols.get("A-1")
        if not a1_protocol:
            print("❌ 未找到A-1协议")
            return False

        # 恢复占位符并提取变量
        source_template_restored = a1_protocol.template_content
        if a1_protocol.jinja_placeholders:
            source_template_restored = converter.renderer._restore_jinja_placeholders(
                source_template_restored,
                a1_protocol.jinja_placeholders
            )

        variables = extractor.extract_variables(
            source_template_restored,
            test_input,
            a1_protocol.array_markers
        )

        expected_vars = {"phone_type", "person"}
        actual_vars = set(variables.keys())

        if not expected_vars.issubset(actual_vars):
            print(f"❌ 变量提取不完整。期望: {expected_vars}, 实际: {actual_vars}")
            return False

        print(f"✅ 成功提取变量: {variables}")
        return True

    def test_protocol_conversion(self):
        """测试协议转换"""
        if not self.loader:
            return False

        # 测试输入
        test_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        converter = self.loader.get_converter()

        # 执行A->B转换
        result = converter.convert("A", "B", test_input)

        if not result.success:
            print(f"❌ 转换失败: {result.error}")
            return False

        if not result.result:
            print("❌ 转换结果为空")
            return False

        # 验证转换结果结构
        if "name" not in result.result or "slots" not in result.result:
            print("❌ 转换结果结构不正确")
            return False

        print(f"✅ 转换成功:")
        print(f"  匹配协议: {result.matched_protocol}")
        print(f"  提取变量: {result.variables}")
        print(f"  转换结果: {json.dumps(result.result, indent=2, ensure_ascii=False)}")

        return True

    def test_cross_family_conversion(self):
        """测试跨协议族转换"""
        if not self.loader:
            return False

        converter = self.loader.get_converter()

        # 测试A->C转换
        test_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        result = converter.convert("A", "C", test_input)

        if not result.success:
            print(f"❌ A->C转换失败: {result.error}")
            return False

        print(f"✅ A->C转换成功: {result.matched_protocol}")
        return True

    def test_edge_cases(self):
        """测试边界条件"""
        if not self.loader:
            return False

        converter = self.loader.get_converter()

        # 测试空输入
        try:
            result = converter.convert("A", "B", {})
            # 空输入应该失败或返回空结果，但不应该崩溃
            print("✅ 空输入处理正常")
        except Exception as e:
            print(f"❌ 空输入导致异常: {e}")
            return False

        # 测试无效协议族
        try:
            result = converter.convert("INVALID", "B", {"test": "data"})
            if result.success:
                print("❌ 无效协议族不应该转换成功")
                return False
            print("✅ 无效协议族正确拒绝")
        except Exception as e:
            print(f"❌ 无效协议族导致异常: {e}")
            return False

        return True

    def test_performance(self):
        """测试性能"""
        if not self.loader:
            return False

        import time

        converter = self.loader.get_converter()
        test_input = {
            "domain": "telephone",
            "action": "DIAL",
            "slots": {
                "category": "mobile",
                "name": "Alice",
                "raw_name": "Alice Smith"
            }
        }

        # 执行多次转换测试性能
        start_time = time.time()
        for i in range(10):
            result = converter.convert("A", "B", test_input)
            if not result.success:
                print(f"❌ 第{i+1}次转换失败")
                return False
        end_time = time.time()

        avg_time = (end_time - start_time) / 10
        print(f"✅ 10次转换平均耗时: {avg_time*1000:.2f}ms")

        if avg_time > 1.0:  # 如果平均超过1秒，认为性能有问题
            print("⚠️ 转换性能可能需要优化")
            return False

        return True

def main():
    """主函数"""
    tester = YAMLSystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()