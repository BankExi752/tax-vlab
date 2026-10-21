# -*- coding: utf-8 -*-
"""V1.10.3 专项：注册/提交后出现结果卡片（含对错、状态、建议），且无弹窗 dlg_ok"""
from streamlit.testing.v1 import AppTest

APP = r"C:\Users\孔鑫璇\Doubao\chats\2026-10-20\new-chat-4\app-src\main_app.py"
fails = []
def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + info if info else ""))
    if not cond:
        fails.append(name)

at = AppTest.from_file(APP, default_timeout=90)
at.run()

# 注册页填表
inp = {i.key: i for i in at.text_input}
inp["reg_class"].set_value("财务2301")
inp["reg_sid"].set_value("T20261021A")
inp["reg_name"].set_value("小白学生")
at.run()
reg = [b for b in at.button if b.key == "reg_enter"]
check("找到注册按钮", len(reg) == 1)
reg[0].click()
at.run()
# 结果卡片应出现在 markdown（含注册成功标题 + 状态 + 建议）
allt = " ".join(str(getattr(e, "value", "")) for e in at.markdown if getattr(e, "value", ""))
check("无弹窗 dlg_ok 按钮", not any(b.key == "dlg_ok" for b in at.button))
check("卡片含注册成功", "注册成功" in allt)
check("卡片含当前状态行", "当前状态" in allt and "稽查风险" in allt)
check("卡片含下一步建议", "下一步建议" in allt)

# 未全答提交 S2 → 结果卡片（warning）
nav2 = [b for b in at.sidebar.button if b.key == "nav_2"]
if nav2:
    nav2[0].click(); at.run()
    sub = [b for b in at.button if b.key == "s2_submit"]
    if sub:
        sub[0].click(); at.run()
        t3 = " ".join(str(getattr(e, "value", "")) for e in at.markdown if getattr(e, "value", ""))
        check("S2 未全答卡片出现", "未作答" in t3 and "下一步建议" in t3, t3[:120])

print("\n==== 结果卡片专项结果:", "ALL PASS" if not fails else f"FAILED: {fails}", "====")
import sys; sys.exit(0 if not fails else 1)
