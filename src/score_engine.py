# -*- coding: utf-8 -*-
"""四层信号灯评分引擎。

判定流程：
1. L1 红灯扫描：任一命中 -> 直接判"高危"，不进入计分。
2. L2/L3 黄灯计分：量化指标（0/1/2）+ 定性信号（0/1）累计。
3. L4 人工信号叠加：强信号（欠薪/社保欠缴/裁员不赔偿）权重 2，普通信号权重 1。
4. 输出风险等级（绿/黄/红）与行动建议。

数据格式见 data/sample_company.json。
"""

# 各层指标定义（key -> 中文名）
L1_ITEMS = {
    "audit_opinion": "非标审计意见",
    "dishonest": "失信被执行/限高",
    "regulatory_investigation": "监管立案调查",
    "insolvency": "资不抵债",
    "high_deposit_high_debt": "存贷双高",
}

L2_ITEMS = {
    "cashflow_quality": "现金流质量",
    "solvency": "偿债能力",
    "earnings_quality": "盈利质量",
    "receivables_inventory": "应收与存货质量",
}

L3_ITEMS = {
    "pledge_reduction": "股权质押/减持",
    "related_party": "关联交易",
    "penalty_inquiry": "处罚与问询函",
    "key_personnel": "关键人事变动",
    "external_guarantee": "对外担保",
    "high_interest_financing": "高息融资",
}

# L4：值 -> (中文名, 权重)；权重 2 为强信号
L4_ITEMS = {
    "salary_delay": ("欠薪/工资延迟", 2),
    "social_security_arrears": ("社保公积金欠缴", 2),
    "layoff_compensation": ("裁员不赔偿", 2),
    "hiring_freeze": ("招聘冻结/HC缩减", 1),
    "office_shrink": ("办公收缩搬迁", 1),
}

# 黄灯总分（L2+L3）分级阈值
YELLOW_SCORE = 3   # 总分 >= 3 且 < 6 -> 黄
RED_SCORE = 6      # 总分 >= 6 -> 红

LEVELS = {"green": "绿", "yellow": "黄", "red": "红"}

ADVICE = {
    "green": "财务与治理信号正常，可正常入职或继续在职观察。",
    "yellow": "存在值得跟踪的风险点：请保持警惕，按季度复查工资发放节奏、社保到账与公开数据变化。",
    "red": "存在致命风险或资金链断裂迹象：入职前应慎重考虑；在职中应尽快准备替代方案，并保留工资条、劳动合同、社保记录等证据，必要时咨询劳动法维权渠道。",
}


class RiskError(ValueError):
    """输入数据格式错误。"""


def _require(obj, key, container_name):
    if not isinstance(obj, dict) or key not in obj:
        raise RiskError("数据缺少 %s 段（%s）" % (container_name, key))
    return obj[key]


def _check_bool(value, name):
    if not isinstance(value, bool):
        raise RiskError("%s 必须是 true/false" % name)


def _check_int(value, name, lo, hi):
    if not isinstance(value, int) or isinstance(value, bool):
        raise RiskError("%s 必须是 %d-%d 的整数" % (name, lo, hi))
    if value < lo or value > hi:
        raise RiskError("%s 超出范围 %d-%d" % (name, lo, hi))


def evaluate(data):
    """根据指标数据评估公司风险，返回结构化结果。"""
    if not isinstance(data, dict):
        raise RiskError("输入必须是 JSON 对象")

    company = data.get("company", "未知公司")
    evaluated_at = data.get("evaluated_at", "")

    l1 = _require(data, "l1", "L1 红灯")
    l2 = _require(data, "l2", "L2 量化")
    l3 = _require(data, "l3", "L3 定性")
    l4 = _require(data, "l4", "L4 人工")

    # 1. L1 红灯扫描
    l1_hits = []
    for key, name in L1_ITEMS.items():
        value = l1.get(key, False)
        _check_bool(value, "L1." + key)
        if value:
            l1_hits.append(name)

    # 2. L2 量化计分（每项 0=正常 1=关注 2=恶化）
    l2_score = 0
    l2_detail = []
    for key, name in L2_ITEMS.items():
        value = l2.get(key, 0)
        _check_int(value, "L2." + key, 0, 2)
        l2_score += value
        if value > 0:
            l2_detail.append("%s(%d)" % (name, value))

    # 3. L3 定性计分（每项 0=未命中 1=命中）
    l3_score = 0
    l3_hits = []
    for key, name in L3_ITEMS.items():
        value = l3.get(key, 0)
        _check_int(value, "L3." + key, 0, 1)
        l3_score += value
        if value:
            l3_hits.append(name)

    # 4. L4 人工信号（强信号权重 2，普通信号权重 1）
    l4_hits = []
    l4_score = 0
    for key, (name, weight) in L4_ITEMS.items():
        value = l4.get(key, 0)
        _check_int(value, "L4." + key, 0, 1)
        if value:
            l4_hits.append(name)
            l4_score += weight
    strong_hits = [name for key, (name, w) in L4_ITEMS.items()
                   if w == 2 and l4.get(key, 0)]

    # 5. 等级判定：红灯 > 人工强信号 > 黄灯累计
    if l1_hits:
        level = "red"
    elif len(strong_hits) >= 2:
        level = "red"
    else:
        yellow_score = l2_score + l3_score
        if yellow_score >= RED_SCORE:
            level = "red"
        elif yellow_score >= YELLOW_SCORE:
            level = "yellow"
        else:
            level = "green"
        # 单个强人工信号：绿灯至少升为黄灯
        if len(strong_hits) == 1 and level == "green":
            level = "yellow"

    return {
        "company": company,
        "evaluated_at": evaluated_at,
        "level": level,
        "level_label": LEVELS[level],
        "l1_hits": l1_hits,
        "l2_score": l2_score,
        "l2_detail": l2_detail,
        "l3_score": l3_score,
        "l3_hits": l3_hits,
        "l4_score": l4_score,
        "l4_hits": l4_hits,
        "advice": ADVICE[level],
    }
