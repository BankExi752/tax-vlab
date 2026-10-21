# -*- coding: utf-8 -*-
"""V1.10.3 专项：注册成功弹窗出现 + 关闭按钮可点"""
from streamlit.testing.v1 import AppTest
import io

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
# 弹窗应出现：dlg_ok 按钮 + 标题"注册成功"
ok = [b for b in at.button if b.key == "dlg_ok"]
check("注册后弹出对话框(dlg_ok 出现)", len(ok) == 1, f"buttons={[b.key for b in at.button][:12]}")
allt = " ".join(str(getattr(e, "value", "")) for e in at.markdown if getattr(e, "value", ""))
check("弹窗含注册成功标题", "注册成功" in allt, allt[:120])
# 点"知道了"关闭
ok[0].click()
at.run()
ok2 = [b for b in at.button if b.key == "dlg_ok"]
check("关闭后 dlg_ok 消失", len(ok2) == 0)

# 未全答提交 S2 → 弹窗（warning）
nav2 = [b for b in at.sidebar.button if b.key == "nav_2"]
if nav2:
    nav2[0].click(); at.run()
    sub = [b for b in at.button if b.key == "s2_submit"]
    if sub:
        sub[0].click(); at.run()
        ok3 = [b for b in at.button if b.key == "dlg_ok"]
        check("S2 未全答拦截弹窗出现", len(ok3) == 1, f"buttons={[b.key for b in at.button][:14]}")
        t3 = " ".join(str(getattr(e, "value", "")) for e in at.markdown if getattr(e, "value", ""))
        check("弹窗含未作答提示", "未作答" in t3, t3[:150])

print("\n==== 弹窗专项结果:", "ALL PASS" if not fails else f"FAILED: {fails}", "====")
import sys; sys.exit(0 if not fails else 1)
