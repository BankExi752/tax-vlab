# -*- coding: utf-8 -*-
"""金税四期下“业—票—税—信”多源异构数据耦合推演与合规裁量虚拟仿真实验
====================================================
Streamlit 教学应用 V1.0（2026 中国仿真创新应用大赛 · 仿真教学创新设计方向）

依据《税法虚拟仿真实验项目计划书_最终版_V5.2》实现：
- 19 个交互节点（S1—S19），课内主线 90 分钟，满分合计 173 分；
- 增值税 / 消费税 / 企业所得税 / 个人所得税四税联动“算账闭环”；
- 凭证可信度 P 指标、进销匹配率、税负率、证据链闭合度等核心指标；
- 财务—稽查双角色对抗、规则引擎定性（无问题 / 一般违规 / 偷税）、
  参数扰动随机种子、AI 提分辅导（规则型）与学习反馈闭环；
- 成绩评定：实验操作 60% + 实验报告与理论测评 30% + 综合考核 10%。

引擎层为模块级纯函数（可冒烟测试）；UI 层以 st.session_state 驱动。
"""
import hashlib
import html as _html
import re

import pandas as pd
import streamlit as st

APP_VERSION = "V1.0"

# ============================================================================
# 一、常量与元数据（与计划书 V5.2 严格对齐）
# ============================================================================

# 19 步元数据：(序号, 步骤名称, 合理用时(分钟), 满分, 成绩类型)
STEPS = [
    (1,  "案例认领与董事会 KPI",              2,  3, "预习"),
    (2,  "税制理论快测（小白三件套）",        4,  5, "预习"),
    (3,  "发票查验与凭证可信度 P 值初评",     5, 10, "操作"),
    (4,  "四流一致性校验与凭证生成",          5,  8, "操作"),
    (5,  "增值税申报与算账闭环",              6, 12, "操作"),
    (6,  "消费税申报与成套拆分筹划",          6, 13, "操作"),
    (7,  "进销匹配率预警与稽查风险条",        6, 10, "操作 + 报告"),
    (8,  "异常凭证进项转出（抽 1 题）",       5, 12, "操作"),
    (9,  "企税汇算清缴与捐赠时间选择（分支）", 6, 15, "操作"),
    (10, "个税申报与年终奖拆分博弈（分支）",  6, 14, "操作"),
    (11, "筹划方案设计与三维自评",            4, 12, "报告"),
    (12, "合规判定（规则为主）",              5,  8, "报告"),
    (13, "稽查员取证（对抗前手）",            5, 10, "操作"),
    (14, "财务合规抗辩（模板化）",            6, 10, "报告"),
    (15, "定性裁量与绩效结算",                6, 10, "报告"),
    (16, "实验报告草稿生成",                  2,  3, "报告"),
    (17, "AI 提分辅导与个性化练习",           5, 10, "教师评价"),
    (18, "最终版报告生成与提交",              3,  3, "报告 + 教师"),
    (19, "学习反馈收集与二次优化",            3,  5, "教师评价"),
]
STEP_FULL = 173  # 19 步满分合计

# 案例数据包（计划书第八章，金额单位：万元，另有注明者除外）
CASES = {
    "零售店": {
        "name": "案例 A · 零售店纳税人身份选择", "tax": "增值税",
        "sales": 420.0, "input_cost": 280.0, "vat_rate": 0.13,
        "core": "一般纳税人 vs 小规模纳税人（3% 减按 1%）",
        "policy": "《增值税暂行条例》；财政部 税务总局公告 2023 年第 19 号",
    },
    "化妆品厂": {
        "name": "案例 B · 化妆品礼盒成套拆分", "tax": "消费税",
        "cream": 800.0, "tool": 200.0, "rate": 0.15,
        "core": "应税消费品与非应税消费品分开核算（财税〔2016〕103 号）",
        "policy": "《消费税暂行条例》及其实施细则；财税〔2016〕103 号（高档化妆品 15%）",
    },
    "商贸公司": {
        "name": "案例 C/D · 捐赠分年扣除 + 年终奖拆分", "tax": "企业所得税 / 个人所得税",
        "profit": 100.0, "donation": 20.0, "limit12": 12.0, "cit_rate": 0.25,
        "salary": 12.0, "deduction": 6.0,
        "core": "公益性捐赠分年扣除（递延纳税）与年终奖单独计税最优拆分",
        "policy": "《企业所得税法》第九条；财税〔2018〕15 号；财税〔2018〕164 号",
    },
}

# 12 张数电票：(票号, 来源分≤40, 签章分≤30, 可追溯分≤30) → P 值 = 三项之和，P<50 为异常票
INVOICES = [
    ("FP2025001", 40, 30, 30), ("FP2025002", 36, 28, 26),
    ("FP2025003", 34, 26, 24), ("FP2025004", 30, 26, 22),
    ("FP2025005", 28, 24, 22), ("FP2025006", 26, 22, 20),
    ("FP2025007", 24, 22, 18), ("FP2025008", 22, 20, 16),
    ("FP2025009", 20, 18, 14), ("FP2025010", 18, 18, 14),
    ("FP2025011", 10, 20, 14), ("FP2025012",  8, 10, 12),
]
ABNORMAL_INVOICES = [inv[0] for inv in INVOICES if inv[1] + inv[2] + inv[3] < 50]

# 税制理论快测（S2）题库：5 题
QUIZ_S2 = [
    {"q": "现行增值税一般纳税人认定标准中，年应征增值税销售额一般为（　）以上。",
     "options": ["100 万元", "300 万元", "500 万元", "1000 万元"], "ans": 2},
    {"q": "下列各项中，属于消费税应税消费品的是（　）。",
     "options": ["高档化妆品", "普通护肤品", "家用空调", "手机"], "ans": 0},
    {"q": "企业发生的公益性捐赠支出，在年度利润总额（　）以内的部分准予在计算应纳税所得额时扣除。",
     "options": ["5%", "10%", "12%", "25%"], "ans": 2},
    {"q": "居民个人取得全年一次性奖金，可选择按（　）单独计算纳税的优惠政策。",
     "options": ["工资薪金并入综合所得", "单独计税（不并入综合所得）", "劳务报酬", "经营所得"], "ans": 1},
    {"q": "“四流一致”通常指合同流、发票流、资金流与（　）保持一致。",
     "options": ["物流", "信息流", "人才流", "数据流"], "ans": 0},
]

# 负面词 / 正面词（S12 合规判定三层评分中的“关键词匹配 + 负面词过滤”）
NEGATIVE_WORDS = ["不开票", "私户收款", "私账", "虚假拆分", "白条入账", "两套账", "虚开发票", "阴阳合同"]
POSITIVE_WORDS = ["四流一致", "如实申报", "合规", "开具发票", "取得合法凭证", "纳税调增", "进项转出", "分开核算"]

# 定性结局概率（参数扰动随机种子驱动，计划书：无问题 41% / 一般违规 36% / 偷税 23%）
OUTCOME_WEIGHTS = {"无问题": 41, "一般违规": 36, "偷税": 23}

# S10 个税案例：3 名自由职业者（劳务报酬预扣）+ 2 名员工（工资预扣），口径：不考虑附加税费、
# 社保与专项附加扣除
S10_PERSONS = [
    {"id": "自由职业者甲", "type": "劳务报酬", "amount": 3.0, "tax": 0.52},
    {"id": "自由职业者乙", "type": "劳务报酬", "amount": 2.0, "tax": 0.32},
    {"id": "自由职业者丙", "type": "劳务报酬", "amount": 1.2, "tax": 0.192},
    {"id": "员工一", "type": "工资薪金", "amount": 9.6, "tax": 0.108},
    {"id": "员工二", "type": "工资薪金", "amount": 7.2, "tax": 0.036},
]

# ============================================================================
# 二、税制规则引擎（模块级纯函数，供冒烟测试直接断言）
# ============================================================================

def calc_p(source, seal, trace):
    """凭证可信度 P = 来源分(40) + 签章分(30) + 可追溯分(30)；P<50 的发票不得抵扣。"""
    p = source + seal + trace
    return p, p < 50


def abnormal_invoices():
    """返回 12 张票中 P<50 的异常票票号列表（系统算 P 但不直接标红）。"""
    return [inv[0] for inv in INVOICES if inv[1] + inv[2] + inv[3] < 50]


def calc_vat(mode):
    """案例 A：销售额 420 万、进项 280 万。
    mode='general' 一般纳税人：420×13% − 280×13% = 18.2 万；
    mode='small'   小规模纳税人：420×1% = 4.2 万（现行 3% 减按 1%）。
    返回 (应纳增值税万元, 税负率, 税后净利润万元)。
    """
    sales, cost = 420.0, 280.0
    if mode == "general":
        tax = sales * 0.13 - cost * 0.13
    elif mode == "small":
        tax = sales * 0.01
    else:
        raise ValueError(mode)
    profit = sales - cost - tax
    return round(tax, 2), round(tax / sales * 100, 2), round(profit, 2)


def calc_consumption(mode):
    """案例 B：面霜 800 元（15%）+ 化妆工具 200 元。
    成套销售按全额最高税率：1000×15% = 150 元；分开核算仅就应税化妆品：800×15% = 120 元。"""
    if mode == "set":
        return 150.0, 1000.0
    return 120.0, 800.0


def calc_cit_plan(mode):
    """案例 C：会计利润 100 万（已含 20 万捐赠支出）、限额 12 万、税率 25%。
    mode='once'  一次性捐赠：纳税调增 8 万，应纳税所得 108 万，当年所得税 27 万；
    mode='two'   分两年捐赠：第 1 年捐 12 万、第 2 年捐 8 万，两年合计抵税效果相同（递延纳税）。
    返回 (纳税调增万, 应纳税所得万, 当年所得税万, 教学结论)。
    """
    if mode == "once":
        adjust, taxable, tax = 8.0, 108.0, 27.0
        note = "当年所得税 27 万；超限额 8 万结转 3 年扣除，第 2 年可再抵税 8×25%=2 万。"
    elif mode == "two":
        adjust, taxable, tax = 0.0, 100.0, 25.0
        note = "第 1 年捐 12 万全额扣除、第 2 年捐 8 万全额扣除，两年合计抵税效果与一次性捐赠相同；"
        note += "仅改变纳税现金流节奏（递延纳税），属风险筹划而非节税筹划。"
    else:
        raise ValueError(mode)
    return adjust, taxable, tax, note


def calc_iit(mode):
    """案例 D：年薪 12 万、减除费用 6 万（不考虑社保与专项附加扣除）。
    mode='all_salary'   全部作为工资：应纳税所得 6 万，6万×10%−2520 = 3480 元；
    mode='split'        最优拆分：工资 9.6 万（应纳税所得 3.6 万 ×3% = 1080 元）
                        + 年终奖 2.4 万（单独计税 2.4 万 ×3% = 720 元），合计 1800 元。"""
    if mode == "all_salary":
        return 0.3480, "全部工资：3480 元"
    if mode == "split":
        return 0.1800, "工资 9.6 万（1080 元）+ 年终奖 2.4 万（720 元）= 1800 元（最优）"
    raise ValueError(mode)


def calc_match_rate(input_tax, output_tax):
    """进销匹配率 = 进项税额 / 销项税额；低于行业阈值触发预警。"""
    if output_tax <= 0:
        return 0.0
    return round(input_tax / output_tax * 100, 2)


def calc_tax_burden(tax_payable, sales):
    """税负率 = 应纳税额 / 应税销售额。"""
    if sales <= 0:
        return 0.0
    return round(tax_payable / sales * 100, 2)


def calc_evidence_closure(fixed_classes, total=4):
    """证据链闭合度 = 已固定证据类数 / 应固定证据类数（合同/资金/物流/发票）。"""
    return round(fixed_classes / total * 100, 2)


def judge_text(text):
    """S12 合规判定（规则为主）：命中负面词 → (0 分, 偷税倾向, 预警)；否则按正面词命中加分。
    返回 (score, risk_delta, message)。满分 8 分。"""
    if not text:
        return 0, 10, "未提交方案文本，无法判定"
    hit_neg = [w for w in NEGATIVE_WORDS if w in text]
    if hit_neg:
        return 0, 40, "命中负面词【" + "、".join(hit_neg) + "】，直接判 0 分并触发预警"
    hit_pos = [w for w in POSITIVE_WORDS if w in text]
    score = min(8, len(hit_pos) * 2)
    msg = "命中正面词【" + "、".join(hit_pos[:3]) + "】" if hit_pos else "未命中关键表述"
    return score, 0, msg


def parse_policy_number(text):
    """提取政策文件号（如“财税〔2016〕103 号”），供 S11/S14 校验。"""
    m = re.findall(r"[（(]?\s*(?:财税|国税|财会|国家税务总局公告)[〔\[(]?\s*\d{4}\s*[〕\]）)]?\s*\d+\s*号", text)
    return m


def derive_outcome(seed_str, risk_points, negative_hit, abnormal_handled, evidence_closure):
    """S15 定性裁量逻辑（规则引擎主导 + 参数扰动种子）：
    - 命中负面词或风险值≥80 → 偷税；
    - 异常票未正确转出、或风险值≥40、或证据闭合度<75% → 一般违规；
    - 其余按随机种子在 无问题/一般违规 之间按权重（41/36）推演。
    返回 (定性, 说明)。"""
    if negative_hit or risk_points >= 80:
        return "偷税", "命中负面词或稽查风险值触顶，证据链倾向偷税定性"
    if (not abnormal_handled) or risk_points >= 40 or evidence_closure < 75:
        return "一般违规", "存在异常凭证未规范转出 / 预警指标未处理 / 证据闭合度不足"
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16) % 100
    if h < 41:
        return "无问题", "扰动种子命中无问题区间（41%），规则与证据链均无异常"
    return "一般违规", "扰动种子命中一般违规区间（36%），建议补充筹划说明"


def credit_after_outcome(outcome, credit_before=100):
    """纳税信用分变化：无问题 +5；一般违规 −20；偷税 −50（联合惩戒后果推演）。"""
    if outcome == "无问题":
        return min(100, credit_before + 5), "+5（诚信纳税激励）"
    if outcome == "一般违规":
        return max(0, credit_before - 20), "−20（纳税信用降级预警）"
    return max(0, credit_before - 50), "−50（信用等级大幅下调，触发联合惩戒）"


def calc_final_score(step_score, report_score, comp_score):
    """实验成绩（百分制）= 操作 60% + 报告理论 30% + 综合 10%。
    实验操作成绩 =（19 步实际得分 ÷ 173）× 100 × 60%；报告与综合满分 100 分。"""
    op = step_score / STEP_FULL * 100 * 0.6
    return round(op + report_score * 0.3 + comp_score * 0.1)


def risk_accumulate(risk_points, add):
    return min(100, max(0, risk_points + add))


# ============================================================================
# 三、SVG 可视化工具（雷达图 / 仪表盘 / 风险条 / 四流耦合图）
# ============================================================================

def _esc(s):
    return _html.escape(str(s), quote=True)


def radar_svg(values, labels, title="税负雷达图", size=320):
    """四轴雷达图（得分率 0–100），用于报告生成与结算页。"""
    n = len(labels)
    cx, cy, r = size / 2, size / 2 - 8, size * 0.34
    def pt(i, ratio):
        ang = -90 + i * (360 / n)
        import math
        rad = math.radians(ang)
        return (cx + r * ratio * math.cos(rad), cy + r * ratio * math.sin(rad))
    parts = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
             f'xmlns="http://www.w3.org/2000/svg" style="font-family:sans-serif;font-size:11px">']
    for ring in (25, 50, 75, 100):
        pts = " ".join(f"{pt(i, ring/100)[0]:.1f},{pt(i, ring/100)[1]:.1f}" for i in range(n))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#d8dee9" stroke-width="1"/>')
    for i in range(n):
        x, y = pt(i, 1)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#d8dee9" stroke-width="1"/>')
        lx, ly = pt(i, 1.28)
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle">{_esc(labels[i])}</text>')
    pts = " ".join(f"{pt(i, max(0, min(100, values[i]))/100)[0]:.1f},{pt(i, max(0, min(100, values[i]))/100)[1]:.1f}"
                   for i in range(n))
    parts.append(f'<polygon points="{pts}" fill="rgba(31,119,180,0.35)" stroke="#1f77b4" stroke-width="2"/>')
    parts.append(f'<text x="{size/2}" y="{size-6}" text-anchor="middle" font-size="12" fill="#333">{_esc(title)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def gauge_svg(value, max_value, label, unit="%", size=240, warn_low=0, warn_high=0):
    """半圆仪表盘：value 相对 max_value 的占比；warn_low/warn_high 为预警区间（数值，非占比）。"""
    import math
    ratio = max(0, min(1, value / max_value))
    angle = 180 + ratio * 180  # 半圆从 180°(左) 到 360°(右)
    cx, cy, r = size / 2, size * 0.72, size * 0.30
    parts = [f'<svg width="{size}" height="{int(size*0.62)}" viewBox="0 0 {size} {int(size*0.62)}" '
             f'xmlns="http://www.w3.org/2000/svg" style="font-family:sans-serif">']
    parts.append(f'<path d="M {cx-r},{cy} A {r},{r} 0 0 1 {cx+r},{cy}" fill="none" stroke="#e5e9f0" stroke-width="14"/>')
    if warn_high > 0:
        # 预警区（红段）
        wa = 180 + (warn_high / max_value) * 180
        parts.append(f'<path d="M {cx-r},{cy} A {r},{r} 0 0 1 {cx+r},{cy}" fill="none" stroke="#ff4d4f" '
                     f'stroke-width="14" stroke-dasharray="{(cx+r-(cx-r))*3.14159*(warn_high/max_value)*0.5} 10000"/>')
    ang = math.radians(angle)
    nx, ny = cx + r * 0.82 * math.cos(ang), cy + r * 0.82 * math.sin(ang)
    parts.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#1f77b4" stroke-width="3"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="#1f77b4"/>')
    parts.append(f'<text x="{cx}" y="{cy+30}" text-anchor="middle" font-size="22" font-weight="bold" fill="#333">{value}</text>')
    parts.append(f'<text x="{cx}" y="{cy+48}" text-anchor="middle" font-size="12" fill="#666">{_esc(label)}（{unit}）</text>')
    parts.append("</svg>")
    return "".join(parts)


def risk_bar_svg(risk_points, size=520):
    """稽查风险条：0–100，绿→黄→红 三段。"""
    pct = max(0, min(100, risk_points))
    w, h = size, 26
    def seg(x0, x1, color):
        return f'<rect x="{x0}" y="0" width="{x1-x0}" height="{h}" fill="{color}" rx="4"/>'
    parts = [f'<svg width="{w}" height="{h+18}" viewBox="0 0 {w} {h+18}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(seg(0, int(w*0.6), "#52c41a"))
    parts.append(seg(int(w*0.6), int(w*0.85), "#faad14"))
    parts.append(seg(int(w*0.85), w, "#ff4d4f"))
    parts.append(f'<rect x="{int(w*pct/100)-2}" y="-4" width="4" height="{h+8}" fill="#111" rx="2"/>')
    parts.append(f'<text x="{w-8}" y="{h+15}" text-anchor="end" font-size="12" fill="#666">稽查风险值 {pct}/100</text>')
    parts.append("</svg>")
    return "".join(parts)


def flows_svg(size=760):
    """业—票—税—信 四流耦合示意图。"""
    w, h = size, 190
    nodes = [
        ("业务流", "采购 / 销售 / 捐赠 / 薪酬", 40, 60, "#1f77b4"),
        ("票据流", "数电票 / 异常凭证 / P 指标", 220, 60, "#2ca02c"),
        ("税款流", "增值税 / 消费税 / 企税 / 个税", 400, 60, "#ff7f0e"),
        ("信用流", "纳税信用 / 风险条 / 定性裁量", 580, 60, "#d62728"),
    ]
    parts = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
             f'style="font-family:sans-serif">']
    for i in range(len(nodes) - 1):
        x1 = nodes[i][2] + 150
        parts.append(f'<line x1="{x1}" y1="90" x2="{nodes[i+1][2]}" y2="90" stroke="#bbb" stroke-width="2" '
                     f'stroke-dasharray="6 4"/>')
        parts.append(f'<text x="{(x1+nodes[i+1][2])/2}" y="82" text-anchor="middle" font-size="10" fill="#888">耦合推演</text>')
    for name, sub, x, y, color in nodes:
        parts.append(f'<rect x="{x}" y="{y}" width="150" height="60" rx="8" fill="{color}" opacity="0.92"/>')
        parts.append(f'<text x="{x+75}" y="{y+26}" text-anchor="middle" fill="#fff" font-size="14" font-weight="bold">{_esc(name)}</text>')
        parts.append(f'<text x="{x+75}" y="{y+46}" text-anchor="middle" fill="#fff" font-size="10">{_esc(sub)}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ============================================================================
# 四、session_state 初始化与公共工具
# ============================================================================

DEFAULT_STATE = {
    "started": False, "case": "", "kpi_confirmed": False, "role": "财务",
    "scores": {}, "risk_points": 0, "credit_score": 100, "current_step": 1,
    "quiz_done": False, "quiz_score": 0, "quiz_attempt": 0,
    "s3_marked": [], "s3_done": False, "s4_balanced": False, "s4_flow": False, "s4_done": False,
    "s5_mode": "general", "s5_done": False, "s6_mode": "set", "s6_done": False,
    "s7_done": False, "s8_seed": "", "s8_done": False, "s9_done": False, "s10_done": False,
    "s11_done": False, "s12_done": False, "s13_done": False, "s14_done": False,
    "s15_done": False, "s16_done": False, "s17_done": False, "s18_done": False, "s19_done": False,
    "s11_text": "", "s12_text": "", "s14_citation": "", "s17_correct": False,
    "outcome": "", "outcome_note": "", "s19_filled": False,
    "report_html": "", "final_score": None, "role_swap_used": False,
}


def init_state():
    for k, v in DEFAULT_STATE.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get(key, default=None):
    return st.session_state.get(key, default)


def setv(key, value):
    st.session_state[key] = value


def steps_done_count():
    return sum(1 for s in STEPS if s[0] in st.session_state.get("scores", {}))


def total_score():
    return round(sum(st.session_state.get("scores", {}).values()), 2)


def step_title(n):
    for s in STEPS:
        if s[0] == n:
            return s
    return None


def step_header(n):
    """展示计划书要求的“目标要求 / 合理用时 / 赋分模型 / 成绩类型”四元组。"""
    meta = step_title(n)
    if not meta:
        return
    _, name, mins, full, stype = meta
    st.markdown(
        f'<div style="background:#f4f7fb;border:1px solid #dbe4f0;border-left:4px solid #1f77b4;'
        f'border-radius:6px;padding:10px 14px;margin-bottom:8px">'
        f'<span style="font-size:17px;font-weight:700;color:#1a3b66">S{n} · {_esc(name)}</span>'
        f'<div style="font-size:12px;color:#5a6b85;margin-top:4px">'
        f'合理用时：{mins} 分钟 ｜ 满分：{full} 分 ｜ 成绩类型：{stype}</div></div>',
        unsafe_allow_html=True,
    )


def score_badge(n, score=None):
    full = step_title(n)[3]
    got = score if score is not None else st.session_state.get("scores", {}).get(n)
    if got is None:
        return f'<span style="color:#999;font-size:12px">未完成（满分 {full} 分）</span>'
    color = "#52c41a" if got >= full * 0.6 else "#faad14"
    return f'<span style="color:{color};font-weight:700;font-size:13px">已得分 {got:g} / {full} 分</span>'


def record(n, score, risk_add=0):
    """记录步骤得分并累积稽查风险值。"""
    s = st.session_state
    s["scores"][n] = round(score, 2)
    s["risk_points"] = risk_accumulate(s["risk_points"], risk_add)
    s[f"s{n}_done"] = True


def dependency_warning(text):
    st.warning(text)


# ============================================================================
# 五、各步骤 UI 渲染
# ============================================================================

def render_s1():
    step_header(1)
    st.markdown("**目标要求**：登录系统认领脱敏案例企业，查看金税四期预警基线，接收董事会 KPI："
                "3 年有效税负率 ≤ 行业基线、零重大处罚。")
    case_opts = ["零售店（增值税主线 · 案例 A）", "化妆品厂（消费税主线 · 案例 B）", "商贸公司（企税 / 个税综合线 · 案例 C/D）"]
    choice = st.radio("认领案例企业", case_opts, key="s1_case_choice")
    case_val = choice.split("（")[0]  # 落库值：零售店 / 化妆品厂 / 商贸公司
    st.markdown(f"**预警基线（金税四期）**：行业税负率预警区间 2%–8% ｜ 进销匹配率阈值 ≥ 70% ｜ "
                f"稽查风险值上限 100 ｜ 纳税信用分初始 100。")
    if st.button("确认认领并接收董事会 KPI", key="s1_confirm", type="primary"):
        setv("case", case_val)
        setv("started", True)
        setv("kpi_confirmed", True)
        record(1, 3)
        st.success("已认领【" + case_val + "】，KPI 确认完成，得分 +3。可进入 S2 预习。")
        st.rerun()


def render_s2():
    step_header(2)
    st.markdown("**目标要求**：5 题理论快测（增值税身份 / 消费税应税范围 / 捐赠扣除 / 年终奖计税），"
                "限时 4 分钟；低于 3 分阻断并重测。")
    if get("quiz_done"):
        st.success(f"快测已完成，当前得分 {get('quiz_score')} / 5（满分 5 分）。")
        return
    answers = {}
    for i, item in enumerate(QUIZ_S2):
        answers[i] = st.radio(f"第 {i+1} 题 · {item['q']}", item["options"],
                              key=f"s2_q{i}", index=None)
    if st.button("提交快测", key="s2_submit", type="primary"):
        score = sum(1 for i, item in enumerate(QUIZ_S2)
                    if answers.get(i) is not None and answers[i] == item["options"][item["ans"]])
        setv("quiz_score", score)
        setv("quiz_attempt", get("quiz_attempt", 0) + 1)
        if score < 3:
            setv("quiz_done", False)
            st.error(f"得分 {score}/5，低于 3 分：弹出 10 秒错题提示后可立即重测。")
            wrong = [i for i, item in enumerate(QUIZ_S2)
                     if answers.get(i) is None or answers[i] != item["options"][item["ans"]]]
            if wrong:
                st.info("错题提示：" + "；".join(f"第 {i+1} 题【{QUIZ_S2[i]['q']}】正确答案："
                                                f"{QUIZ_S2[i]['options'][QUIZ_S2[i]['ans']]}" for i in wrong))
        else:
            setv("quiz_done", True)
            record(2, score)
            st.success(f"快测通过，得分 {score}/5。")
            st.rerun()


def render_s3():
    step_header(3)
    st.markdown("**目标要求**：对 12 张数电票逐一查验，系统为每张票计算 P = 来源 40 + 签章 30 + 可追溯 30，"
                "标出 P＜50 的异常票（系统不直接标红，由你判断）。查验 1 张给 0.5 分，准确标出 2 张异常票再给 4 分。")
    df = pd.DataFrame(
        [{"票号": inv[0], "来源分": inv[1], "签章分": inv[2], "可追溯分": inv[3],
          "P 值（系统计算）": inv[1] + inv[2] + inv[3]} for inv in INVOICES]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    marked = st.multiselect("请标注你认为 P＜50 的异常票（系统不会替你标红）",
                            [inv[0] for inv in INVOICES], key="s3_marked")
    if st.button("提交查验结果", key="s3_submit", type="primary"):
        true_abn = set(abnormal_invoices())
        marked_set = set(marked)
        score = 12 * 0.5 + 2.0 * len(marked_set & true_abn)
        miss = true_abn - marked_set
        risk_add = 0 if not miss else 20
        record(3, score, risk_add)
        if miss:
            st.warning(f"漏标异常票：{','.join(sorted(miss))}，稽查风险值 +20。")
        st.success(f"S3 得分 {score:g} / 10。")
        st.rerun()


def render_s4():
    step_header(4)
    st.markdown("**目标要求**：系统已预填凭证（关键科目留空），你核对并补全；系统校验合同 / 发票 / 资金 / 物流"
                "四流是否一致，断裂则保存按钮变灰。借贷平衡给 5 分，四流一致再给 3 分。")
    st.markdown("**采购凭证（预填）**：借：库存商品 280 万 ｜ 借：应交税费—应交增值税（进项税额）**（待填）**"
                " ｜ 贷：银行存款 **（待填）**")
    input_tax = st.number_input("进项税额（万元）", value=36.4, step=0.1, key="s4_input_tax")
    credit = st.number_input("贷方银行存款（万元）", value=316.4, step=0.1, key="s4_credit")
    balanced = abs(280 + input_tax - credit) < 0.05
    st.markdown("**四流状态**：合同 √ 已签订 ｜ 发票 √ 已取得 ｜ 资金 √ 已支付 ｜ 物流 **✗ 运输单据缺失（疑似断裂）**")
    flow_choice = st.radio("四流是否一致？（系统提示存在断裂点）", ["一致", "存在断裂"], key="s4_flow_choice")
    if st.button("保存凭证", key="s4_submit", type="primary"):
        score = 5 if balanced else 0
        risk_add = 0
        if flow_choice == "存在断裂":
            score += 3
        else:
            risk_add = 15
            st.warning("四流存在断裂（物流单据缺失）却判定一致，稽查风险值 +15。")
        record(4, min(8, score), risk_add)
        if not balanced:
            st.error("借贷不平衡：280 + 进项税额 ≠ 贷方金额，请核对后重试。")
        st.success(f"S4 得分 {min(8, score):g} / 8。")
        st.rerun()


def render_s5():
    step_header(5)
    st.markdown("**目标要求**：系统取数生成增值税主表，复核应纳税额；在身份选择界面比较一般纳税人与小规模"
                "税负，改动身份触发全链重算（算账闭环：增值税 → 税后净利润实时变化）。"
                "表内勾稽全对 10 分，税负率落入正常区间（3%–8%）再加 2 分。")
    c = CASES["零售店"]
    st.markdown(f"**案例 A**：销售额 {c['sales']:g} 万元、可抵扣进项 {c['input_cost']:g} 万元。")
    mode = st.radio("纳税人身份选择（改动即触发全链重算）",
                    ["一般纳税人（13%）", "小规模纳税人（3% 减按 1%）"], key="s5_mode")
    mode_val = "general" if mode.startswith("一般") else "small"
    tax, burden, profit = calc_vat(mode_val)
    col1, col2, col3 = st.columns(3)
    col1.metric("应纳增值税", f"{tax} 万元")
    col2.metric("税负率", f"{burden} %")
    col3.metric("税后净利润（算账闭环）", f"{profit} 万元")
    confirm = st.number_input("确认应纳税额（万元）", value=tax, key="s5_amount")
    in_range = 3 <= burden <= 8
    if st.button("提交复核", key="s5_submit", type="primary"):
        correct = abs(confirm - tax) < 0.05
        score = 10 if correct else 0
        if correct and in_range:
            score += 2
        record(5, min(12, score))
        st.success(f"S5 得分 {min(12, score):g} / 12（税负率 {burden}%{'落入正常区间 +2' if in_range and correct else ''}）。")
        st.rerun()


def render_s6():
    step_header(6)
    st.markdown("**目标要求**：［消费税专属］填消费税申报表；案例 B 面霜 800 元（15%）+ 工具 200 元，"
                "成套缴 150 元，默认选中“分开签订合同、分别开票”降为 120 元，允许改选以对比税额差异。"
                "申报表全对 8 分，正确执行拆分筹划再加 5 分。")
    c = CASES["化妆品厂"]
    mode = st.radio("成套销售 vs 分开核算",
                    ["成套销售（组合销售按全额最高税率）", "分开签订合同、分别开票（默认推荐）"],
                    key="s6_mode", index=1)
    mode_val = "set" if mode.startswith("成套") else "split"
    tax, base = calc_consumption(mode_val)
    tax_set, _ = calc_consumption("set")
    col1, col2 = st.columns(2)
    col1.metric("应纳消费税", f"{tax} 元")
    col2.metric("成套销售应纳（对比）", f"{tax_set} 元", delta=f"{tax - tax_set:+.0f} 元")
    confirm = st.number_input("确认申报税额（元）", value=tax, key="s6_amount")
    if st.button("提交申报", key="s6_submit", type="primary"):
        score = 8 if abs(confirm - tax) < 0.5 else 0
        if mode_val == "split":
            score += 5
        record(6, min(13, score))
        st.success(f"S6 得分 {min(13, score):g} / 13。")
        st.rerun()


def render_s7():
    step_header(7)
    st.markdown("**目标要求**：手动计算进销匹配率 = 进项税额 / 销项税额，判断仪表盘颜色（阈值 70%），"
                "每次不合规操作累积稽查风险值。公式对 4 分，颜色判断一致 4 分，风险条未触顶再加 2 分。")
    st.markdown("当期数据：销项税额 **54.6 万元**（销售额 420 万 × 13%），进项税额 **36.4 万元**。")
    ratio_input = st.number_input("进销匹配率（%，请自行计算）", value=66.67, step=0.01, key="s7_ratio")
    color_input = st.radio("仪表盘应显示的颜色（阈值 70%，低于触发预警）",
                           ["绿色（正常）", "黄色（关注）", "红色（预警）"], key="s7_color")
    true_color = "红色（预警）" if ratio_input < 70 else "绿色（正常）"
    if st.button("提交判断", key="s7_submit", type="primary"):
        exact = abs(calc_match_rate(36.4, 54.6) - ratio_input) < 0.01
        score = 4 if exact else 0
        if color_input == true_color:
            score += 4
        risk_add = 0 if color_input == true_color else 15
        if get("risk_points", 0) < 100:
            score += 2
        record(7, min(10, score), risk_add)
        st.success(f"S7 得分 {min(10, score):g} / 10（系统匹配率 {calc_match_rate(36.4, 54.6)}%，"
                   f"应为【{true_color}】）。")
        st.rerun()


def render_s8():
    step_header(8)
    st.markdown("**目标要求**：针对 S3 异常票做进项税额转出分录，系统随机抽 1 组种子（红冲时点 / 异常类型）"
                "导致金额不同。金额准确 6 分，借贷方向正确 4 分，种子匹配再加 2 分。")
    if not get("s3_done"):
        dependency_warning("检测到 S3 发票查验尚未完成，建议返回 S3 核对异常票后再做进项转出。")
    st.markdown("**跨步骤防呆**：S3（异常票）→ S8（进项转出）→ S5（增值税）→ S7（预警指标）→ S15（定性）主依赖链。")
    if get("s8_seed") == "":
        seed_kinds = [("当月红冲 · 失控发票", 0.00), ("跨期红冲 · 作废发票", 0.03), ("当月红冲 · 伪造发票", 0.05)]
        import random as _r
        _r.seed(get("quiz_attempt", 0) * 7 + 3)
        kind, penalty = seed_kinds[_r.randint(0, len(seed_kinds) - 1)]
        setv("s8_seed", kind)
        setv("s8_penalty", penalty)
    kind = get("s8_seed")
    penalty = get("s8_penalty", 0.0)
    st.info(f"本次抽取种子：**{kind}**。异常票 FP2025011 对应进项税额 8.5 万元，"
            f"转出系数 = 1 + {penalty:.2%}（红冲时点与异常类型耦合）。")
    amount = st.number_input("进项税额转出金额（万元）", value=8.5, step=0.001, key="s8_amount")
    debit = st.radio("会计分录方向", ["借：主营业务成本，贷：应交税费—进项税额转出", "借：应交税费，贷：银行存款"], key="s8_debit")
    correct_amount = 8.5 * (1 + penalty)
    if st.button("提交分录", key="s8_submit", type="primary"):
        score = 6 if abs(amount - correct_amount) < 0.01 else 0
        score += 4 if debit.startswith("借：主营业务成本") else 0
        score += 2 if abs(amount - correct_amount) < 0.01 else 0
        record(8, min(12, score), 0 if score >= 10 else 10)
        st.success(f"S8 得分 {min(12, score):g} / 12（本种子正确答案 {correct_amount:.3f} 万元）。")
        st.rerun()


def render_s9():
    step_header(9)
    st.markdown("**目标要求**：填 A105000；案例 C 会计利润 100 万（已含 20 万捐赠支出）、税法扣除限额 12 万，"
                "需纳税调增 8 万，比较一次性捐赠与分两年捐赠并理解递延纳税逻辑。调增额落入允许区间 10 分，"
                "捐赠分年选择正确再加 5 分。本步为税收学 / 会计学分支选做。")
    c = CASES["商贸公司"]
    adj = st.number_input("A105000 纳税调增金额（万元）", value=8.0, step=0.5, key="s9_adj")
    plan = st.radio("捐赠时间安排", ["一次性捐赠（当年全部捐出）", "分两年捐赠（第 1 年 12 万、第 2 年 8 万）"], key="s9_plan")
    if st.button("提交汇算", key="s9_submit", type="primary"):
        score = 10 if abs(adj - 8.0) < 0.1 else 0
        correct_plan = plan.startswith("分两年")
        if correct_plan:
            score += 5
        record(9, min(15, score))
        st.success(f"S9 得分 {min(15, score):g} / 15。")
        _, taxable, tax, note = calc_cit_plan("once" if plan.startswith("一次性") else "two")
        st.info(f"教学结论（{plan}）：应纳税所得 {taxable:g} 万、当年所得税 {tax:g} 万。{note}")
        st.rerun()


def render_s10():
    step_header(10)
    st.markdown("**目标要求**：处理 3 名自由职业者 + 2 名员工；案例 D 年薪 12 万、减除 6 万，比较全部工资"
                "缴 3480 元与工资 9.6 万 + 年终奖 2.4 万缴 1800 元。申报每人对给 2 分满分 10 分，"
                "拆分方案选择正确再加 4 分。本步为税收学 / 财管分支选做。")
    answers = {}
    for p in S10_PERSONS:
        answers[p["id"]] = st.number_input(f"{p['id']}（{p['type']}，预扣税额 万元）",
                                           value=round(p["tax"], 3), step=0.001, key=f"s10_{p['id']}")
    split = st.radio("案例 D 最优拆分方案", ["全部作为工资（3480 元）", "工资 9.6 万 + 年终奖 2.4 万（1800 元）"], key="s10_split")
    if st.button("提交申报", key="s10_submit", type="primary"):
        score = sum(2 for p in S10_PERSONS if abs(answers[p["id"]] - p["tax"]) < 0.001)
        if split.startswith("工资 9.6"):
            score += 4
        record(10, min(14, score))
        st.success(f"S10 得分 {min(14, score):g} / 14。")
        st.rerun()


def render_s11():
    step_header(11)
    st.markdown("**目标要求**：基于 S5—S10 的降税操作撰写 ≤200 字筹划方案，须含政策依据文件号"
                "（如财税〔2016〕103 号）与关键表述。含政策依据与关键表述给 8 分，三维自评合理加 4 分。")
    text = st.text_area("筹划方案（≤200 字，须含政策依据文件号）", height=140, key="s11_text")
    if text and len(text) > 200:
        st.warning(f"已超 200 字（当前 {len(text)} 字），将按 200 字口径判定。")
    c1 = st.radio("合规维度自评", ["高", "中", "低"], key="s11_c1")
    c2 = st.radio("经济维度自评", ["高", "中", "低"], key="s11_c2")
    c3 = st.radio("可执行维度自评", ["高", "中", "低"], key="s11_c3")
    if st.button("提交方案", key="s11_submit", type="primary"):
        score = 0
        if parse_policy_number(text):
            score += 4
        hit = [w for w in ["拆分", "分开核算", "单独计税", "加计扣除", "进项转出", "调增"] if w in text]
        if hit:
            score += 4
        if (c1 != "低") and (c2 != "低") and (c3 != "低"):
            score += 4
        record(11, min(12, score), 15 if ("不开票" in text or "私户" in text) else 0)
        st.success(f"S11 得分 {min(12, score):g} / 12。")
        st.rerun()


def render_s12():
    step_header(12)
    st.markdown("**目标要求**：系统以“关键词匹配 + 负面词过滤 + 教师兜底”三层评分：命中“不开票”“私户收款”"
                "“虚假拆分”等负面词直接判 0 分并弹预警；合规定性由规则引擎给出。本步给分以关键词与负面词命中为准。")
    text = st.text_area("粘贴/输入你的操作描述或筹划方案以供合规判定", height=120, key="s12_text")
    if st.button("提交判定", key="s12_submit", type="primary"):
        score, risk_add, msg = judge_text(text)
        record(12, score, risk_add)
        if score == 0:
            st.error(msg + " → 合规判定：偷税倾向，预警！")
        else:
            st.success(f"S12 得分 {score}/8。{msg}")
        st.rerun()


def render_s13():
    step_header(13)
    st.markdown("**目标要求**：切换稽查角色，固定合同 / 资金 / 物流 / 发票四类证据，计算证据链闭合度"
                " = 已固定证据类数 / 应固定证据类数。闭合度计算正确 6 分，四类证据齐全再给 4 分。")
    st.info("当前对抗角色：【税务稽查】——同一证据包，从稽查视角审视。")
    ev = st.multiselect("已固定的证据类（可多选）", ["合同", "资金", "物流", "发票"],
                        default=["合同", "发票", "资金"], key="s13_ev")
    closure_input = st.number_input("证据链闭合度（%）", value=75.0, step=1.0, key="s13_closure")
    if st.button("提交取证", key="s13_submit", type="primary"):
        true_closure = calc_evidence_closure(len(ev))
        score = 6 if abs(true_closure - closure_input) < 0.01 else 0
        if len(ev) == 4:
            score += 4
        record(13, min(10, score), 0 if len(ev) >= 3 else 10)
        st.success(f"S13 得分 {min(10, score):g} / 10（闭合度应为 {true_closure}%）。")
        st.rerun()


def render_s14():
    step_header(14)
    st.markdown("**目标要求**：切回财务角色，从给定 A / B / C / D 四条抗辩话术模板中选择最合理的一条并完成"
                "条款引用。选择正确 6 分，条款引用准确加 4 分。")
    st.info("当前对抗角色：【企业财务】——合规抗辩视角。")
    options = [
        "A. 我司已按实际经营开具发票，四流一致，申报无差错，恳请复核。",
        "B. 客户要求不开发票是行业惯例，不应认定违规。",
        "C. 资金通过老板私人账户结算更灵活，与税务无关。",
        "D. 发票金额可适当调整以匹配报表，属正常账务处理。",
    ]
    choice = st.radio("选择最合理的抗辩话术", options, key="s14_choice")
    citation = st.text_input("条款/文件号引用（如《增值税暂行条例》或财税〔2018〕164 号）", key="s14_citation")
    if st.button("提交抗辩", key="s14_submit", type="primary"):
        score = 6 if choice.startswith("A.") else 0
        if citation and (parse_policy_number(citation) or "条例" in citation or "公告" in citation):
            score += 4
        record(14, min(10, score))
        st.success(f"S14 得分 {min(10, score):g} / 10。")
        st.rerun()


def render_s15():
    step_header(15)
    st.markdown("**目标要求**：系统依据 S3—S14 证据与规则给出“无问题 / 一般违规 / 偷税”三类定性，"
                "计算税负率与纳税信用分变化。定性与证据链一致 8 分，税负与信用分计算正确加 2 分。")
    s = st.session_state
    if not s.get("s15_done"):
        seed = f"{s.get('case','')}|{s.get('s8_seed','')}|{s.get('quiz_attempt',0)}|{s.get('risk_points',0)}"
        negative_hit = s.get("scores", {}).get(12) == 0
        abnormal_handled = s.get("scores", {}).get(8, 0) >= 6
        closure = s.get("scores", {}).get(13, 0) >= 6
        ev_closure = 100.0 if closure else 50.0
        outcome, note = derive_outcome(seed, s["risk_points"], negative_hit, abnormal_handled, ev_closure)
        setv("outcome", outcome)
        setv("outcome_note", note)
    outcome = s["outcome"]
    st.markdown(f"**系统定性结果**：<span style='font-size:22px;font-weight:800;"
                f"color:{'#52c41a' if outcome=='无问题' else ('#faad14' if outcome=='一般违规' else '#ff4d4f')}'>"
                f"{outcome}</span>", unsafe_allow_html=True)
    st.info(s["outcome_note"])
    credit_new, credit_note = credit_after_outcome(outcome, s["credit_score"])
    col1, col2 = st.columns(2)
    col1.metric("纳税信用分", f"{s['credit_score']} → {credit_new}", delta=credit_note)
    col2.metric("稽查风险值", f"{s['risk_points']} / 100")
    agree = st.radio("定性结果与证据链是否一致？", ["一致", "不一致"], key="s15_agree")
    credit_input = st.radio("信用分变化档位", ["+5（无问题）", "−20（一般违规）", "−50（偷税）"], key="s15_credit")
    if st.button("确认结算", key="s15_submit", type="primary"):
        score = 8 if agree == "一致" else 0
        expect = "+5（无问题）" if outcome == "无问题" else ("−20（一般违规）" if outcome == "一般违规" else "−50（偷税）")
        if credit_input == expect:
            score += 2
        setv("credit_score", credit_new)
        record(15, min(10, score))
        st.success(f"S15 得分 {min(10, score):g} / 10。")
        st.rerun()


def render_s16():
    step_header(16)
    st.markdown("**目标要求**：系统生成报告草稿（操作轨迹 / 得分 / 分支图 / 税负雷达图），学生预览核对，"
                "分数可随 S17 加分更新。草稿生成成功给 3 分。")
    if st.button("生成报告草稿", key="s16_submit", type="primary"):
        setv("report_html", build_report_html())
        record(16, 3)
        st.success("报告草稿已生成（操作轨迹 / 得分明细 / 税负雷达图），得分 +3。")
        st.rerun()
    if get("report_html"):
        st.markdown(get("report_html"), unsafe_allow_html=True)


def render_s17():
    step_header(17)
    st.markdown("**目标要求**：AI 拆解失分因子推送 3 分钟微课 + 2 道同类题，完成练习可加回部分分数"
                "（最高 +10% 权重）。练习全对 6 分，完成观看 2 分，教师认可 2 分。")
    s = st.session_state
    lost = [step_title(n)[1] for n in s.get("scores", {}) if s["scores"][n] < step_title(n)[3] * 0.6]
    if lost:
        st.info("**AI 失分因子拆解**：" + "；".join(f"S{n} {name}" for n, name in
                [(n, step_title(n)[1]) for n in s["scores"] if s["scores"][n] < step_title(n)[3] * 0.6]))
        st.markdown("**推荐微课（3 分钟）**：数电票查验与异常凭证识别 ｜ 四税申报勾稽 ｜ 筹划方案政策依据写法。")
    else:
        st.success("当前无失分步骤，AI 建议保持节奏进入报告环节。")
    q1 = st.radio("同类题 1：面霜 800 元（15%）与工具 200 元成套销售，应纳消费税（元）？",
                  ["120", "150", "180"], key="s17_q1")
    q2 = st.radio("同类题 2：年薪 12 万、减除 6 万，全部按工资计税的应纳税额（元）？",
                  ["1800", "3480", "5790"], key="s17_q2")
    watched = st.checkbox("已完成 3 分钟微课观看", key="s17_watch")
    if st.button("提交练习", key="s17_submit", type="primary"):
        score = 6 if q1 == "150" and q2 == "3480" else 0
        score += 2 if watched else 0
        score += 2  # 教师认可（演示环境默认认可）
        setv("s17_correct", q1 == "150" and q2 == "3480")
        record(17, min(10, score))
        st.success(f"S17 得分 {min(10, score):g} / 10。")
        st.rerun()


def render_s18():
    step_header(18)
    st.markdown("**目标要求**：系统按 S17 最终得分生成最终版 PDF 报告，学生确认提交；教师端回填评语与微调分。"
                "提交成功 2 分，教师评价 1 分。")
    if st.button("生成最终版报告并提交", key="s18_submit", type="primary"):
        setv("report_html", build_report_html(final=True))
        record(18, 2)
        st.success("最终版报告已生成并提交，得分 +2。")
        st.rerun()
    if get("report_html"):
        st.markdown(get("report_html"), unsafe_allow_html=True)
    teacher = st.text_input("教师端评语（可选，填写即视为完成教师评价）", key="s18_teacher")
    if teacher and not st.session_state.get("s18_teacher_done", False):
        record(18, 3)  # 2 + 1（教师评价）
        setv("s18_teacher_done", True)
        st.success("教师评语已回填，S18 总分更新为 3/3。")


def render_s19():
    step_header(19)
    st.markdown("**目标要求**：填写结构化问卷：难度感知、最有收获步骤、最困惑税种、希望增加案例类型、"
                "开放性建议，生成班级反馈热力图。问卷提交完整 3 分，附具体改进建议再加 2 分。")
    diff = st.select_slider("难度感知", options=["很容易", "较容易", "适中", "较难", "很难"], key="s19_diff")
    best = st.selectbox("最有收获的步骤", [f"S{n} {name}" for n, name, _, _, _ in STEPS], key="s19_best")
    conf = st.selectbox("最困惑的税种", ["增值税", "消费税", "企业所得税", "个人所得税"], key="s19_conf")
    more = st.text_input("希望增加的案例类型（可选）", key="s19_more")
    advice = st.text_area("开放性建议（填写可 +2 分）", height=80, key="s19_advice")
    if st.button("提交反馈", key="s19_submit", type="primary"):
        score = 3
        if advice and len(advice) >= 5:
            score += 2
        setv("s19_filled", True)
        record(19, min(5, score))
        st.success(f"S19 得分 {min(5, score):g} / 5，感谢反馈！")
        st.rerun()
    if get("s19_filled"):
        st.markdown("**班级反馈热力图（模拟聚合）**")
        st.markdown(heatmap_svg({"很容易": 8, "较容易": 20, "适中": 42, "较难": 22, "很难": 8}), unsafe_allow_html=True)


# ============================================================================
# 六、报告与结算
# ============================================================================

def build_report_html(final=False):
    """生成实验报告（操作轨迹 / 得分明细 / 税负雷达图 / 成绩）。"""
    s = st.session_state
    rows = "".join(
        f"<tr><td>S{n}</td><td>{_esc(name)}</td><td>{s['scores'].get(n, 0):g}</td><td>{full}</td></tr>"
        for n, name, _, full, _ in STEPS
    )
    radar_vals = radar_axis_values(s)
    radar = radar_svg(radar_vals, ["增值税", "消费税", "企业所得税", "个人所得税"])
    done = steps_done_count()
    step_sc = total_score()
    final = calc_final_score(step_sc, 85, 90) if final else None
    setv("final_score", final)
    html = f"""
    <div style="font-family:'Microsoft YaHei',sans-serif;border:1px solid #dbe4f0;border-radius:10px;
                padding:18px 22px;background:#fff">
      <h3 style="margin:0 0 6px;color:#1a3b66">实验报告{'(最终版)' if final else '(草稿)'}</h3>
      <div style="color:#5a6b85;font-size:13px;margin-bottom:10px">
        案例企业：{_esc(s.get('case','—'))} ｜ 定性结果：{_esc(s.get('outcome','未结算'))}
         ｜ 完成步骤 {done}/19 ｜ 步骤得分 {step_sc:g}/173 ｜ 稽查风险值 {s['risk_points']}/100
         ｜ 纳税信用分 {s['credit_score']}</div>
      <table style="border-collapse:collapse;width:100%;font-size:13px">
        <tr style="background:#f4f7fb"><th style="border:1px solid #dbe4f0;padding:5px">步骤</th>
        <th style="border:1px solid #dbe4f0;padding:5px">名称</th>
        <th style="border:1px solid #dbe4f0;padding:5px">得分</th>
        <th style="border:1px solid #dbe4f0;padding:5px">满分</th></tr>{rows}
        <tr style="background:#fbfaf5"><td colspan="2" style="border:1px solid #dbe4f0;padding:5px;font-weight:700">合计</td>
        <td style="border:1px solid #dbe4f0;padding:5px;font-weight:700">{step_sc:g}</td>
        <td style="border:1px solid #dbe4f0;padding:5px;font-weight:700">173</td></tr>
      </table>
      <div style="margin-top:10px">{radar}</div>
      <div style="font-size:13px;color:#1a3b66;margin-top:8px">实验成绩（百分制）=
        操作 {step_sc}/173×100×60% + 报告 85×30% + 综合 90×10% =
        {calc_final_score(step_sc, 85, 90)} 分</div>
    </div>"""
    return html


def radar_axis_values(s):
    """四税得分率（0–100）：增值税 S5/S7/S8、消费税 S6、企税 S9、个税 S10。"""
    sc = s.get("scores", {})
    def rate(steps, full):
        got = sum(sc.get(n, 0) for n in steps)
        return round(got / full * 100)
    vat_full = step_title(5)[3] + step_title(7)[3] + step_title(8)[3]
    return [rate([5, 7, 8], vat_full), rate([6], step_title(6)[3]),
            rate([9], step_title(9)[3]), rate([10], step_title(10)[3])]


def heatmap_svg(dist):
    """S19 班级反馈热力图（条形聚合）。"""
    total = max(1, sum(dist.values()))
    rows = []
    colors = ["#52c41a", "#7cb305", "#faad14", "#fa8c16", "#ff4d4f"]
    for i, (k, v) in enumerate(dist.items()):
        w = int(480 * v / total)
        rows.append(
            f'<text x="8" y="{28 + i*30}" font-size="12" fill="#555">{_esc(k)}</text>'
            f'<rect x="110" y="{20 + i*30}" width="{w}" height="18" rx="4" fill="{colors[i]}"/>'
            f'<text x="{118 + w}" y="{33 + i*30}" font-size="12" fill="#333">{v}%</text>')
    return (f'<svg width="600" height="150" xmlns="http://www.w3.org/2000/svg" '
            f'style="font-family:sans-serif">{"".join(rows)}</svg>')


def render_summary():
    """结算页：最终成绩（60/30/10）+ 雷达图 + 定性。"""
    s = st.session_state
    step_sc = total_score()
    report_guess = 85  # 报告与理论测评（演示环境默认 85，可在 S18 微调）
    comp = 90          # 综合考核（演示环境默认 90）
    final = calc_final_score(step_sc, report_guess, comp)
    setv("final_score", final)
    st.markdown(f"<h2 style='color:#1a3b66'>实验结算</h2>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("步骤得分", f"{step_sc:g} / 173")
    c2.metric("实验成绩（百分制）", f"{final} 分")
    c3.metric("稽查风险值", f"{s['risk_points']} / 100")
    c4.metric("纳税信用分", f"{s['credit_score']}")
    st.markdown("**最终定性**：" + (f"<span style='font-size:20px;font-weight:800;color:{'#52c41a' if s['outcome']=='无问题' else ('#faad14' if s['outcome']=='一般违规' else '#ff4d4f')}'>{s['outcome']}</span>"
                if s.get("outcome") else "未完成 S15 定性结算"), unsafe_allow_html=True)
    st.markdown(radar_svg(radar_axis_values(s), ["增值税", "消费税", "企业所得税", "个人所得税"], "税负能力雷达图"),
                unsafe_allow_html=True)
    st.markdown("成绩构成：实验操作 60% + 实验报告与理论测评 30% + 综合考核 10%")
    if st.button("重新开始实验", key="reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ============================================================================
# 七、主流程
# ============================================================================

def render_sidebar():
    s = st.session_state
    with st.sidebar:
        st.markdown(f"**金税四期虚仿实验**  {APP_VERSION}")
        if not s["started"]:
            st.caption("请先在首页认领案例并召开董事会")
            return
        st.markdown(f"案例企业：**{s.get('case','—')}**")
        role = st.radio("对抗角色", ["财务", "稽查"], key="role_switch")
        setv("role", role)
        done = steps_done_count()
        st.progress(done / len(STEPS), text=f"实验进度 {done}/19")
        st.markdown(risk_bar_svg(s["risk_points"]), unsafe_allow_html=True)
        st.metric("累计得分", f"{total_score():g} / 173")
        for n, name, _, _, _ in STEPS:
            label = f"S{n} {name}"
            if s.get("scores", {}).get(n) is not None:
                label += f"  ✓{s['scores'][n]:g}"
            if st.button(label, key=f"nav_{n}", use_container_width=True):
                setv("current_step", n)
                st.rerun()
        if st.button("结算页", key="nav_summary", use_container_width=True):
            setv("current_step", 99)
            st.rerun()


def render_home():
    st.markdown(
        f"<div style='background:linear-gradient(120deg,#1a3b66,#2c5c9e);border-radius:12px;"
        f"padding:26px 30px;color:#fff'>"
        f"<div style='font-size:12px;letter-spacing:2px;color:#bcd3f0'>2026 中国仿真创新应用大赛 · 仿真教学创新设计方向</div>"
        f"<h1 style='margin:8px 0 4px;font-size:26px;line-height:1.4'>金税四期下“业—票—税—信”多源异构数据<br>"
        f"耦合推演与合规裁量虚拟仿真实验</h1>"
        f"<div style='font-size:13px;color:#dfe9f7;margin-top:6px'>会计学 / 财务管理 / 税收学 ｜ "
        f"税法 · 税务稽查 · 纳税筹划 · 税务会计 ｜ 综合设计型 + 探究型 + 对抗型</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("### 实验导览")
    st.markdown(flows_svg(), unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.metric("交互节点", "19 步（S1—S19）")
    col2.metric("四大税种", "增值税 / 消费税 / 企税 / 个税")
    col3.metric("满分合计", "173 分（课内主线 90 分钟）")
    st.markdown("""
- **引导认知**：案例认领 → 理论快测（S1—S2）
- **基础操作**：发票查验 → 四流校验 → 四税申报（S3—S10）
- **风险研判**：预警指标 → 筹划方案 → 合规判定（S7、S11—S12）
- **双角色对抗**：稽查取证 ↔ 财务抗辩 → 定性裁量（S13—S15）
- **总结复盘**：报告草稿 → AI 提分 → 最终报告 → 学习反馈（S16—S19）
""")
    if not st.session_state.get("started"):
        render_s1()
    else:
        st.info("已在侧边栏按 S1—S19 继续实验，或点击下方按钮回到认领页。")
        if st.button("回到 S1 案例认领", key="back_s1"):
            setv("current_step", 1)
            st.rerun()


def main():
    init_state()
    st.set_page_config(page_title="金税四期·业票税信虚仿实验", page_icon="🧾", layout="wide")
    render_sidebar()
    cur = st.session_state.get("current_step", 1)
    if not st.session_state.get("started") and cur != 1:
        setv("current_step", 1)
        cur = 1
    if cur == 99:
        render_summary()
        return
    if cur == 1:
        render_home()
        return
    # 独立步骤页（侧边栏导航进入）
    st.markdown(f"<div style='font-size:12px;color:#8a97ab;margin-bottom:4px'>金税四期下“业—票—税—信”虚仿实验 · "
                f"步骤 {cur}/19</div>", unsafe_allow_html=True)
    renderers = {2: render_s2, 3: render_s3, 4: render_s4, 5: render_s5, 6: render_s6, 7: render_s7,
                 8: render_s8, 9: render_s9, 10: render_s10, 11: render_s11, 12: render_s12,
                 13: render_s13, 14: render_s14, 15: render_s15, 16: render_s16, 17: render_s17,
                 18: render_s18, 19: render_s19}
    renderers.get(cur, render_home)()
    st.markdown(f"<div style='margin-top:14px;color:#8a97ab;font-size:12px'>—— {APP_VERSION} ｜ "
                f"金税四期下“业—票—税—信”多源异构数据耦合推演与合规裁量虚拟仿真实验 ——</div>",
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
