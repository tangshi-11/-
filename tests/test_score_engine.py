# -*- coding: utf-8 -*-
"""评分引擎单元测试。运行方式：python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from score_engine import evaluate, RiskError


def base_data():
    """一份全绿的基准数据。"""
    return {
        "company": "测试公司",
        "l1": {
            "audit_opinion": False,
            "dishonest": False,
            "regulatory_investigation": False,
            "insolvency": False,
            "high_deposit_high_debt": False,
        },
        "l2": {
            "cashflow_quality": 0,
            "solvency": 0,
            "earnings_quality": 0,
            "receivables_inventory": 0,
        },
        "l3": {
            "pledge_reduction": 0,
            "related_party": 0,
            "penalty_inquiry": 0,
            "key_personnel": 0,
            "external_guarantee": 0,
            "high_interest_financing": 0,
        },
        "l4": {
            "salary_delay": 0,
            "social_security_arrears": 0,
            "layoff_compensation": 0,
            "hiring_freeze": 0,
            "office_shrink": 0,
        },
    }


class TestLevels(unittest.TestCase):
    def test_all_green(self):
        result = evaluate(base_data())
        self.assertEqual(result["level"], "green")
        self.assertEqual(result["level_label"], "绿")

    def test_l1_red_audit(self):
        data = base_data()
        data["l1"]["audit_opinion"] = True
        self.assertEqual(evaluate(data)["level"], "red")

    def test_l1_red_insolvency(self):
        data = base_data()
        data["l1"]["insolvency"] = True
        result = evaluate(data)
        self.assertEqual(result["level"], "red")
        self.assertIn("资不抵债", result["l1_hits"])

    def test_l2_l3_accumulate_yellow(self):
        data = base_data()
        data["l2"]["cashflow_quality"] = 2
        data["l3"]["pledge_reduction"] = 1
        result = evaluate(data)  # 2 + 1 = 3 分 -> 黄
        self.assertEqual(result["level"], "yellow")

    def test_l2_l3_accumulate_red(self):
        data = base_data()
        data["l2"] = {k: 2 for k in data["l2"]}          # 8 分
        data["l3"]["related_party"] = 1                  # +1 -> 9 分
        self.assertEqual(evaluate(data)["level"], "red")

    def test_l4_one_strong_promotes_to_yellow(self):
        data = base_data()
        data["l4"]["salary_delay"] = 1
        result = evaluate(data)  # 单独强信号：绿 -> 黄
        self.assertEqual(result["level"], "yellow")

    def test_l4_two_strong_red(self):
        data = base_data()
        data["l4"]["salary_delay"] = 1
        data["l4"]["social_security_arrears"] = 1
        self.assertEqual(evaluate(data)["level"], "red")


class TestValidation(unittest.TestCase):
    def test_missing_l1_raises(self):
        data = base_data()
        del data["l1"]
        with self.assertRaises(RiskError):
            evaluate(data)

    def test_bad_l2_value_raises(self):
        data = base_data()
        data["l2"]["solvency"] = 5
        with self.assertRaises(RiskError):
            evaluate(data)

    def test_bad_l1_type_raises(self):
        data = base_data()
        data["l1"]["dishonest"] = "yes"
        with self.assertRaises(RiskError):
            evaluate(data)


if __name__ == "__main__":
    unittest.main()
