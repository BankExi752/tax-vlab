# -*- coding: utf-8 -*-
"""V1.10 用户管理与教师端专项测试（Windows 版）"""
import os, sys
from streamlit.testing.v1 import AppTest

APP = r"C:\Users\孔鑫璇\Doubao\chats\2026-10-20\new-chat-4\app-src\main_app.py"
DATA = r"C:\Users\孔鑫璇\Doubao\chats\2026-10-20\new-chat-4\app-src\data"
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

def register(at, klass, sid, name):
    for t, val in [("reg_class", klass), ("reg_sid", sid), ("reg_name", name)]:
        next(x for x in at.text_input if x.key == t).set_value(val)
    next(b for b in at.button if b.key == "reg_enter").click()
    at.run()

# ===== 1. 门控 =====
print("==== 1. 学生实名门控 ====")
at = AppTest.from_file(APP, default_timeout=120)
at.run()
check("未注册只见登录页", "学生实名登录" in all_text(at))
check("看不到实验首页", "金税四期下" not in all_text(at) or "实验地图" not in all_text(at))
keys = [t.key for t in at.text_input]
check("班级/学号/姓名三项输入", all(k in keys for k in ("reg_class", "reg_sid", "reg_name")), str(keys))
next(b for b in at.button if b.key == "reg_enter").click(); at.run()
check("空提交拦截提示", "不能为空" in all_text(at))
next(x for x in at.text_input if x.key == "reg_class").set_value("财务2301")
next(b for b in at.button if b.key == "reg_enter").click(); at.run()
check("缺学号/姓名拦截", "学号不能为空" in all_text(at) and "姓名不能为空" in all_text(at))
register(at, "财务2301", "V110001", "张三")
check("注册成功进入首页", "实验地图" in all_text(at))
check("会话已登记学生", at.session_state["student_registered"] is True
      and at.session_state["student"]["姓名"] == "张三")
at2 = AppTest.from_file(APP, default_timeout=120)
at2.run()
register(at2, "财务2301", "V110001", "李四")
check("重复学号被拦截", "该学号已注册" in all_text(at2))
check("重复者未进入实验", at2.session_state.get("student_registered") is not True)

# ===== 2. 操作日志落库 =====
print("\n==== 2. 操作日志落库 ====")
logs_path = os.path.join(DATA, "logs.csv")
check("logs.csv 已生成", os.path.exists(logs_path))
lines = open(logs_path, encoding="utf-8-sig").read()
check("日志含注册记录", "V110001" in lines and "注册" in lines)
launch = [b for b in at.button if "确认认领并接收董事会 KPI" in str(b.label)][0]
launch.click(); at.run()
nav2 = [b for b in at.sidebar.button if b.key == "nav_2"][0]
nav2.click(); at.run()
radios = {r.key: r for r in at.radio}
correct = {"s2_q0": "500 万元", "s2_q1": "高档化妆品", "s2_q2": "12%",
           "s2_q3": "单独计税（不并入综合所得）", "s2_q4": "物流"}
for k, v in correct.items():
    radios[k].set_value(v)
submit2 = [b for b in at.button if b.key == "s2_submit"][0]
submit2.click(); at.run()
lines = open(logs_path, encoding="utf-8-sig").read()
check("日志含提交 S2 记录", "提交 S2" in lines and "5/5 分" in lines)
sb_md = " ".join(str(m.value) for m in at.sidebar.markdown)
check("侧边栏显示学生信息", "V110001" in sb_md or "张三" in sb_md)

# ===== 3. 教师端 =====
print("\n==== 3. 教师端后台 ====")
t = AppTest.from_file(APP, default_timeout=120)
t.run()
tbtn = [b for b in t.button if b.key == "gate_teacher"]
check("登录页有教师端入口", len(tbtn) == 1)
tbtn[0].click(); t.run()
check("教师端口令门控出现", any(x.key == "teacher_pwd" for x in t.text_input)
      and any(b.key == "teacher_login" for b in t.button))
next(x for x in t.text_input if x.key == "teacher_pwd").set_value("wrong")
next(b for b in t.button if b.key == "teacher_login").click(); t.run()
check("错误口令拦截", "口令错误" in all_text(t))
next(x for x in t.text_input if x.key == "teacher_pwd").set_value("tax2026")
next(b for b in t.button if b.key == "teacher_login").click(); t.run()
check("教师端进入成功", "学生成绩表" in all_text(t) or "学生档案" in all_text(t))
check("成绩表含已注册学生", "V110001" in all_text(t) or "张三" in all_text(t))
dkeys = [d.key for d in t.download_button]
check("按班级导出成绩按钮", "teacher_export_scores" in dkeys, str(dkeys)[:200])
check("导出操作日志按钮", "teacher_export_logs" in dkeys)
check("评估输入与保存", "teacher_comment" in [x.key for x in t.text_area]
      and "teacher_save_assess" in [b.key for b in t.button])

# ===== 4. 学生自导出（总结复盘窗格） =====
print("\n==== 4. 学生自导出 ====")
r = AppTest.from_file(APP, default_timeout=120)
r.run()
register(r, "财务2302", "V110002", "李四")
launch = [b for b in r.button if "确认认领并接收董事会 KPI" in str(b.label)][0]
launch.click(); r.run()
navr = [b for b in r.sidebar.button if b.key == "nav_review"][0]
navr.click(); r.run()
rdkeys = [d.key for d in r.download_button]
check("我的成绩档案导出按钮", "my_scores_csv" in rdkeys, str(rdkeys)[:200])
check("得分明细导出按钮", "my_detail_csv" in rdkeys)
check("我的操作日志导出按钮", "my_logs_csv" in rdkeys)
check("导出口径提示", "导出后自行存档" in all_text(r))

print("\n==== V1.10 专项结果:", "ALL PASS" if not fails else f"FAILED: {fails}", "====")
sys.exit(0 if not fails else 1)
