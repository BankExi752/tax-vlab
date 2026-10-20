# -*- coding: utf-8 -*-
"""冒烟测试：streamlit stub 屏蔽顶层副作用后 exec_module，对税制引擎纯函数加断言。

运行：python smoke_test.py，输出 ALL PASS 才可推送。
"""
import sys, importlib.util, types

APP = r"C:\Users\孔鑫璇\Doubao\chats\2026-10-20\new-chat-4\app-src\main_app.py"

class _Dummy:
    def __getattr__(self, k):
        return lambda *a, **kw: None
    def __setattr__(self, k, v):
        object.__setattr__(self, k, v)
    def __contains__(self, k):
        return True

class _StubMod(types.ModuleType):
    def __getattr__(self, k):
        return lambda *a, **kw: None

stub = _StubMod("streamlit")
stub.session_state = _Dummy()
sys.modules["streamlit"] = stub
sys.modules["pandas"] = importlib.import_module("pandas")

spec = importlib.util.spec_from_file_location("main_app", APP)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

fails = []
def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + info if info else ""))
    if not cond:
        fails.append(name)

# ===== 断言区 =====
# 1. 凭证可信度 P 指标
p, abn = m.calc_p(10, 20, 14)
check("P 指标 44 判异常", p == 44 and abn is True, f"P={p}")
p2, abn2 = m.calc_p(18, 18, 14)
check("P 指标 50 不判异常", p2 == 50 and abn2 is False, f"P={p2}")
check("12 张票恰有 2 张异常", len(m.abnormal_invoices()) == 2,
      str(m.abnormal_invoices()))
check("异常票为 FP2025011/12",
      set(m.abnormal_invoices()) == {"FP2025011", "FP2025012"})

# 2. 增值税（案例 A）
tax, burden, profit = m.calc_vat("general")
check("一般纳税人应纳 18.2 万", abs(tax - 18.2) < 1e-6, f"tax={tax}")
taxs, burdens, profits = m.calc_vat("small")
check("小规模应纳 4.2 万", abs(taxs - 4.2) < 1e-6, f"tax={taxs}")
check("一般纳税人税负率 4.33%", abs(burden - 4.333) < 0.01, f"burden={burden}")
check("算账闭环净利润", abs(profit - 121.8) < 1e-6, f"profit={profit}")

# 3. 消费税（案例 B）
tset, base_set = m.calc_consumption("set")
tsplit, base_split = m.calc_consumption("split")
check("成套应纳 150 元", tset == 150.0, f"tax={tset}")
check("拆分应纳 120 元", tsplit == 120.0, f"tax={tsplit}")

# 4. 企税捐赠（案例 C）
adj, taxable, cit_tax, note = m.calc_cit_plan("once")
check("一次性捐赠调增 8 万", adj == 8.0, f"adj={adj}")
check("应纳税所得 108 万", taxable == 108.0, f"taxable={taxable}")
check("当年所得税 27 万", cit_tax == 27.0, f"tax={cit_tax}")
adj2, tax2, cit2, note2 = m.calc_cit_plan("two")
check("分两年无调增", adj2 == 0.0 and cit2 == 25.0, f"adj={adj2} tax={cit2}")

# 5. 个税（案例 D）
iit_all, _ = m.calc_iit("all_salary")
iit_split, _ = m.calc_iit("split")
check("全部工资 3480 元", abs(iit_all - 0.3480) < 1e-9, f"tax={iit_all}")
check("最优拆分 1800 元", abs(iit_split - 0.1800) < 1e-9, f"tax={iit_split}")

# 6. 进销匹配率 / 税负率
check("进销匹配率 66.67%", abs(m.calc_match_rate(36.4, 54.6) - 66.67) < 0.01,
      f"rate={m.calc_match_rate(36.4, 54.6)}")
check("税负率 4.33%", abs(m.calc_tax_burden(18.2, 420) - 4.333) < 0.01)

# 7. 证据链闭合度
check("闭合度 3/4=75%", m.calc_evidence_closure(3) == 75.0)
check("闭合度 4/4=100%", m.calc_evidence_closure(4) == 100.0)

# 8. 合规判定（负面词 / 正面词）
sc, risk, msg = m.judge_text("我们通过私户收款规避开票")
check("负面词判 0 分", sc == 0 and risk >= 40, f"score={sc} risk={risk} msg={msg}")
sc2, risk2, _ = m.judge_text("我司四流一致并如实申报，取得合法凭证")
check("正面词给分", sc2 >= 4, f"score={sc2}")

# 9. 定性裁量
o1, n1 = m.derive_outcome("seed-x", 95, True, True, 100.0)
check("负面词+风险触顶判偷税", o1 == "偷税", o1)
o2, n2 = m.derive_outcome("seed-x", 0, False, True, 100.0)
check("无异常时可判无问题", o2 in ("无问题", "一般违规"), f"{o2} {n2}")
o3, _ = m.derive_outcome("seed-x", 0, False, False, 100.0)
check("异常未转出判一般违规", o3 == "一般违规", o3)

# 10. 信用分变化
cr, nt = m.credit_after_outcome("偷税", 100)
check("偷税信用分 -50", cr == 50, f"credit={cr}")
cr2, _ = m.credit_after_outcome("无问题", 95)
check("无问题信用分 +5 封顶 100", cr2 == 100, f"credit={cr2}")

# 11. 成绩折算（示例：138 分步骤 + 85 报告 + 90 综合 → 82）
check("成绩折算示例 = 82", m.calc_final_score(138, 85, 90) == 82,
      f"final={m.calc_final_score(138, 85, 90)}")

# 12. 元数据对齐
check("19 步满分合计 173", sum(s[3] for s in m.STEPS) == 173,
      str(sum(s[3] for s in m.STEPS)))
check("19 步用时合计 90 分钟", sum(s[2] for s in m.STEPS) == 90,
      str(sum(s[2] for s in m.STEPS)))
check("19 步数量", len(m.STEPS) == 19, str(len(m.STEPS)))
check("S5/S7/S8 增值税分值合计 34", sum(m.step_title(n)[3] for n in (5, 7, 8)) == 34)
check("政策文件号解析", m.parse_policy_number("依据财税〔2016〕103 号拆分核算") != [],
      str(m.parse_policy_number("依据财税〔2016〕103 号拆分核算")))
check("SVG 雷达可生成", "svg" in m.radar_svg([80, 90, 70, 60], ["增值税", "消费税", "企业所得税", "个人所得税"]))
check("SVG 风险条可生成", "svg" in m.risk_bar_svg(45))
check("四流耦合图可生成", "svg" in m.flows_svg())
check("热力图可生成", "svg" in m.heatmap_svg({"适中": 42}))

# 13. 快测题库
check("快测 5 题", len(m.QUIZ_S2) == 5)
check("快测答案索引合法", all(0 <= q["ans"] < len(q["options"]) for q in m.QUIZ_S2))

# 14. S10 五人预扣税额合计口径（教学简化，不参与总分）
check("S10 五人数据 5 条", len(m.S10_PERSONS) == 5)

print("\n==== 冒烟结果:", "ALL PASS" if not fails else f"FAILED: {fails}", "====")
sys.exit(0 if not fails else 1)
