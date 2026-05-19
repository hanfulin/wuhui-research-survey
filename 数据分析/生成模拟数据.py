# -*- coding: utf-8 -*-
"""
============================================================
  ⚠️ 生成「测试用模拟数据」——严禁用于课题报告 ⚠️
============================================================
用途：在真实问卷数据回收齐之前，先用模拟数据把分析流水线
      （分析.py）跑通、把统计表/图表模板做好。真实数据导出后
      直接替换即可，无需改任何分析代码。

本脚本产出的 CSV：
  · 文件名带「测试用_请勿用于报告」
  · 内含 __数据性质__ 列，每行标注「模拟测试数据(非真实)」
  · 控制台与文件头均有醒目警告

★ 它不是真实样本，不能进《原创性声明》覆盖的任何成果。
   结题报告中的数据必须是问卷星导出的真实作答。

用法：
  py 数据分析/生成模拟数据.py --a 70 --b 18 --c 25
  （--a/--b/--c = 科研/科研管理/财务审计 三卷模拟份数；--seed 固定可复现）
"""
import csv, os, sys, random, argparse, datetime
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wenjuan_schema import QUESTIONS, SCALE, col_header

BANNER = "模拟测试数据(非真实)"

# 量表题按题"极性"设权重：值=各档[完全不符合..完全符合]概率
# 反映现实：政策认知偏低、报销负担重、想要负面清单、过程监管弱
SCALE_W = {
    "q6_policy_clear":  [.10, .26, .34, .22, .08],
    "q7_rule_ready":    [.14, .28, .30, .20, .08],
    "q9_ambiguous":     [.05, .12, .25, .36, .22],
    "a_autonomy":       [.10, .24, .32, .26, .08],
    "a_burden":         [.05, .12, .24, .35, .24],
    "a_redline_clear":  [.06, .18, .34, .30, .12],
    "a_neglist_help":   [.03, .07, .18, .38, .34],
    "a_sys_query":      [.12, .26, .30, .24, .08],
    "b_boundary":       [.12, .28, .32, .22, .06],
    "b_power_worry":    [.05, .14, .30, .34, .17],
    "b_proj_clear":     [.10, .26, .34, .24, .06],
    "b_process_weak":   [.04, .12, .26, .36, .22],
    "b_grade_auth":     [.10, .24, .32, .26, .08],
    "c_segregation":    [.06, .16, .30, .34, .14],
    "c_procure_weak":   [.05, .15, .30, .34, .16],
    "c_surplus":        [.06, .16, .30, .32, .16],
    "c_sys_connect":    [.12, .28, .30, .22, .08],
    "c_ctrl_embed":     [.14, .30, .30, .20, .06],
    "z_overall":        [.08, .22, .38, .26, .06],
}
SCALE_DEFAULT = [.10, .22, .34, .26, .08]

# 单选题各选项权重（顺序对应 schema options）
SINGLE_W = {
    "q3_title":   {"A": [.30, .34, .22, .10, .04], "B": [.05, .25, .15, .05, .50],
                   "C": [.10, .40, .20, .05, .25]},  # 按 q2 角色分别给
    "q4_years":   [.22, .40, .26, .12],
    "q5_join":    {"A": [.28, .46, .20, .06], "B": [.06, .20, .54, .20],
                   "C": [.05, .18, .52, .25]},
    "q8_landing": [.06, .46, .30, .10, .08],
    "a_spend_dist": [.20, .34, .30, .16],
    "a_assistant":  [.16, .40, .34, .10],
    "b_govern":     [.40, .34, .14, .12],
    "b_risk_assess":[.34, .40, .26],
    "c_adjust":     [.40, .34, .08, .18],
    "c_budget_ctrl":[.30, .40, .16, .14],
    "c_audit":      [.30, .42, .16, .12],
    "z_interview":  [.34, .66],
}
SINGLE_DEFAULT_EVEN = True

# 多选题各选项被选概率（独立伯努利；max_pick 时截断）
MULTI_P = {
    "q10_barrier":   {"A": .58, "B": .46, "C": .40, "D": .52, "E": .34, "F": .30, "G": .04},
    "a_why_not_use": {"A": .50, "B": .40, "C": .42, "D": .48, "E": .30, "F": .12},
    "b_risk_stage":  {"A": .30, "B": .26, "C": .70, "D": .58, "E": .34},
}

TEXT_SAMPLES = {
    "a_want_rule":   ["劳务费列支标准", "专家咨询费上限", "设备购置审批口径", ""],
    "a_want_support":["简化报销流程", "配科研财务助理", "明确负面清单", ""],
    "b_auth_advice": ["按金额分级授权", "按事项类型区分", "项目负责人扩大权限", ""],
    "c_want_ctrl":   ["结余资金管理", "采购环节内控前置", "过程动态监管", ""],
    "z_advice":      ["希望加强培训宣传", "系统应互联互通", "审计应前移", "", "", ""],
}

def wchoice(opts, weights):
    return random.choices(opts, weights=weights, k=1)[0]

def gen_row(role, idx):
    """role in A/B/C/D；按分流逻辑只填本卷+通用题，其余留空。"""
    ans = {}
    track = role if role in ("A", "B", "C") else None
    # Q1 知情同意：极少数不同意（用于测试"中止"分支）
    consent = "A" if random.random() > 0.02 else "B"
    for q in QUESTIONS:
        num, f, typ, tr, stem, opts, mx = q
        # 分流：非通用题只在对应卷作答；D/未选 不答任何分卷题
        if tr != "ALL" and tr != track:
            ans[f] = ""
            continue
        if f == "q1_consent":
            ans[f] = "同意，开始填写" if consent == "A" else "不同意"
            continue
        # Q1 不同意 → 后续全空（问卷星中止逻辑）
        if consent == "B":
            ans[f] = ""
            continue
        if f == "q2_role":
            ans[f] = dict(opts)[role]
            continue
        if typ == "scale":
            ans[f] = wchoice(SCALE, SCALE_W.get(f, SCALE_DEFAULT))
        elif typ == "single":
            codes = [c for c, _ in opts]
            w = SINGLE_W.get(f)
            if isinstance(w, dict):
                w = w.get(role, None)
            if w is None:
                w = [1] * len(codes)
            code = wchoice(codes, w)
            ans[f] = dict(opts)[code]
        elif typ == "multi":
            p = MULTI_P.get(f, {})
            picked = [lbl for c, lbl in opts if random.random() < p.get(c, .25)]
            if not picked:
                picked = [random.choice(opts)[1]]
            if mx:
                picked = picked[:mx]
            ans[f] = "┋".join(picked)
        elif typ == "text":
            ans[f] = random.choice(TEXT_SAMPLES.get(f, [""] * 4))
        else:
            ans[f] = ""
    return ans

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=70, help="科研人员卷模拟份数")
    ap.add_argument("--b", type=int, default=18, help="科研管理卷模拟份数")
    ap.add_argument("--c", type=int, default=25, help="财务/审计卷模拟份数")
    ap.add_argument("--d", type=int, default=4, help="其他/未匹配 份数（测试用）")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（可复现）")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    plan = [("A", args.a), ("B", args.b), ("C", args.c), ("D", args.d)]
    rows, sn = [], 1
    base = datetime.datetime(2026, 6, 1, 9, 0, 0)
    for role, n in plan:
        for _ in range(n):
            a = gen_row(role, sn)
            meta = {
                "序号": sn,
                "提交答卷时间": (base + datetime.timedelta(
                    minutes=sn * 7 + random.randint(0, 400))).strftime("%Y-%m-%d %H:%M:%S"),
                "所用时间": f"{random.randint(180, 720)}秒",
                "__数据性质__": BANNER,
            }
            meta.update(a)
            rows.append(meta)
            sn += 1
    random.shuffle(rows)
    for i, r in enumerate(rows, 1):
        r["序号"] = i

    headers = ["序号", "提交答卷时间", "所用时间", "__数据性质__"] + \
              [col_header(q) for q in QUESTIONS]
    field_of = {col_header(q): q[1] for q in QUESTIONS}

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "输出")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "模拟数据_测试用_请勿用于报告.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as fp:
        fp.write("# ⚠️ 本文件为测试用模拟数据，非真实问卷作答，严禁用于课题报告或《原创性声明》覆盖的成果\n")
        w = csv.writer(fp)
        w.writerow(headers)
        for r in rows:
            w.writerow([r.get("序号"), r.get("提交答卷时间"), r.get("所用时间"),
                        r.get("__数据性质__")] +
                       [r.get(field_of[col_header(q)], "") for q in QUESTIONS])

    total = len(rows)
    print("=" * 56)
    print("  [!]  已生成【测试用模拟数据】——严禁用于课题报告  [!]")
    print("=" * 56)
    print(f"  科研卷 A={args.a}  管理卷 B={args.b}  财务卷 C={args.c}  其他 D={args.d}")
    print(f"  合计 {total} 行  ->  {out}")
    print("  下一步：py 数据分析/分析.py --input \"%s\"" % out)
    print("  真实数据回收后：把问卷星导出的 CSV 路径传给 --input 即可，分析代码无需改动。")

if __name__ == "__main__":
    main()
