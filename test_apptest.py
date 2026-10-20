# -*- coding: utf-8 -*-
"""AppTest 端到端：启动实验 → 理论快测 → 增值税申报 → 结算页。

运行：python test_apptest.py，ALL PASS 才可推送。
"""
import sys
from streamlit.testing.v1 import AppTest

APP = r"C:\Users\孔鑫璇\Doubao\chats\2026-10-20\new-chat-4\app-src\main_app.py"
fails = []
def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + info if info else ""))
    if not cond:
        fails.append(name)

def all_text(at, seq_names=("markdown", "success", "info", "caption", "warning", "error")):
    parts = []
    for s in seq_names:
        try:
            for el in getattr(at, s):
                v = getattr(el, "value", None)
                if v:
                    parts.append(str(v))
        except Exception:
            pass
    return " ".join(parts)

at = AppTest.from_file(APP, default_timeout=120)
at.run()

# 1. 首页标题
check("首页含主标题", "金税四期下" in all_text(at))
check("首页含四流导览", "耦合推演" in all_text(at) or "业务流" in all_text(at))

# 2. 启动按钮
launch = [b for b in at.button if "确认认领并接收董事会 KPI" in str(b.label)]
check("找到启动按钮", len(launch) == 1, str([b.label for b in at.button])[:200])
launch[0].click()
at.run()
check("启动后已认领案例", at.session_state["started"] is True)
check("案例落库值为零售店", at.session_state["case"] == "零售店",
      str(at.session_state.get("case")))
check("S1 得分 3", at.session_state["scores"].get(1) == 3,
      str(at.session_state["scores"]))

# 3. 侧边栏导航按钮
navs = [b for b in at.sidebar.button if b.key and str(b.key).startswith("nav_")]
check("侧边栏 19 步导航按钮", len(navs) >= 19, f"{len(navs)} 个")
summary_btn = [b for b in at.sidebar.button if b.key == "nav_summary"]
check("结算页按钮存在", len(summary_btn) == 1)

# 4. 跳转 S2 并完成快测（全对）
nav2 = [b for b in at.sidebar.button if b.key == "nav_2"][0]
nav2.click(); at.run()
check("S2 页渲染", "税制理论快测" in all_text(at))
radios = {r.key: r for r in at.radio}
check("快测 5 题 radio", len([k for k in radios if k.startswith("s2_q")]) == 5,
      str(list(radios.keys())))
correct = {"s2_q0": "500 万元", "s2_q1": "高档化妆品", "s2_q2": "12%",
           "s2_q3": "单独计税（不并入综合所得）", "s2_q4": "物流"}
for k, v in correct.items():
    radios[k].set_value(v)
submit2 = [b for b in at.button if "提交快测" in str(b.label)]
check("快测提交按钮", len(submit2) == 1)
submit2[0].click(); at.run()
check("快测得分 5", at.session_state["quiz_score"] == 5,
      str(at.session_state.get("quiz_score")))
check("S2 得分 5", at.session_state["scores"].get(2) == 5,
      str(at.session_state["scores"]))

# 5. 跳转 S5 完成增值税复核（一般纳税人 18.2 万）
nav5 = [b for b in at.sidebar.button if b.key == "nav_5"][0]
nav5.click(); at.run()
check("S5 页渲染", "增值税申报与算账闭环" in all_text(at))
nins = {n.key: n for n in at.number_input}
check("S5 应纳税额输入框", "s5_amount" in nins, str(list(nins.keys())))
if "s5_amount" in nins:
    nins["s5_amount"].set_value(18.2)
s5btn = [b for b in at.button if "提交复核" in str(b.label)]
check("S5 提交按钮", len(s5btn) == 1)
s5btn[0].click(); at.run()
check("S5 得分 12（勾稽+税负区间）", at.session_state["scores"].get(5) == 12,
      str(at.session_state["scores"].get(5)))

# 6. 跳转 S15 定性自动生成
nav15 = [b for b in at.sidebar.button if b.key == "nav_15"][0]
nav15.click(); at.run()
check("S15 页渲染", "定性裁量与绩效结算" in all_text(at))
check("S15 自动生成定性", at.session_state.get("outcome") in ("无问题", "一般违规", "偷税"),
      str(at.session_state.get("outcome")))

# 7. 结算页
sb = [b for b in at.sidebar.button if b.key == "nav_summary"][0]
sb.click(); at.run()
check("结算页渲染", "实验结算" in all_text(at))
check("最终成绩为整数", isinstance(at.session_state.get("final_score"), int),
      str(at.session_state.get("final_score")))

print("\n==== AppTest 结果:", "ALL PASS" if not fails else f"FAILED: {fails}", "====")
sys.exit(0 if not fails else 1)
