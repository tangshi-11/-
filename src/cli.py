# -*- coding: utf-8 -*-
"""命令行入口：读取公司指标 JSON 文件，输出风险评估报告。

用法：
    python src/cli.py data/sample_company.json
"""
import json
import sys

from score_engine import evaluate, RiskError


def main():
    if len(sys.argv) < 2:
        print("用法: python src/cli.py <数据文件.json>")
        print("示例: python src/cli.py data/sample_company.json")
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("找不到文件: %s" % path)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print("JSON 解析失败: %s" % e)
        sys.exit(1)

    try:
        result = evaluate(data)
    except RiskError as e:
        print("数据格式错误: %s" % e)
        sys.exit(1)

    # 打印报告
    print("=" * 46)
    print("公司：%s" % result["company"])
    print("评估日期：%s" % (result["evaluated_at"] or "未填写"))
    print("=" * 46)
    print("风险等级：%s" % result["level_label"])
    print("-" * 46)
    if result["l1_hits"]:
        print("L1 红灯命中（一票否决）：")
        for name in result["l1_hits"]:
            print("  - %s" % name)
    else:
        print("L1 红灯：未命中")
    print("L2 量化计分：%d 分 %s" % (result["l2_score"], result["l2_detail"]))
    print("L3 定性计分：%d 分 %s" % (result["l3_score"], result["l3_hits"]))
    print("L4 人工信号：%d 分 %s" % (result["l4_score"], result["l4_hits"]))
    print("-" * 46)
    print("建议：%s" % result["advice"])
    print("=" * 46)


if __name__ == "__main__":
    main()
