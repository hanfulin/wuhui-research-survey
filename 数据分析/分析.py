# -*- coding: utf-8 -*-
"""
问卷分析流水线（零依赖，纯标准库）。真实数据与模拟数据通用。

用法：
  py 数据分析/分析.py --input "数据分析/输出/模拟数据_测试用_请勿用于报告.csv"
  # 真实数据：问卷星「分析&下载」导出 CSV，把路径传给 --input 即可，代码无需改

做的事：
  1. 读 CSV（兼容 utf-8-sig / gbk；自动跳过以 # 开头的说明行）
  2. 去标识化：删除 来自IP/来源/地区/经纬度/openid 等可定位列（关键纪律）
  3. 按 Q2 岗位分卷（A科研/B科研管理/C财务审计/D其他）
  4. 统计：各卷回收量、单选/多选频数与占比、量表均值/标准差/五档分布、
          按职称与年限的量表均值交叉
  5. 输出：数据分析/输出/ 下若干 CSV 统计表 + 分析摘要.md
  ⚠️ 若检测到 __数据性质__ 列含“模拟”，摘要全程加“测试模拟数据”水印警告
"""
import csv, os, sys, argparse, statistics, re
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wenjuan_schema import QUESTIONS, SCALE, DROP_META_COLS

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "输出")
ROLE_LABEL = {"A": "科研人员(A卷)", "B": "科研管理(B卷)",
              "C": "财务审计(C卷)", "D": "其他/未匹配"}
SCALE_SCORE = {s: i + 1 for i, s in enumerate(SCALE)}


def read_csv(path):
    raw = None
    for enc in ("utf-8-sig", "gbk", "utf-8"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                raw = f.read()
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        sys.exit(f"无法解码文件：{path}")
    lines = [ln for ln in raw.splitlines() if not ln.lstrip().startswith("#")]
    rdr = csv.reader(lines)
    rows = list(rdr)
    return rows[0], rows[1:]


def qnum(header):
    """从问卷星表头取题号：'6.xxx' / '6、xxx' / '6．xxx' -> 6"""
    m = re.match(r"\s*(\d+)\s*[\.、．\:：]", header)
    return int(m.group(1)) if m else None


def build_colmap(headers):
    """题号 -> 列下标。兼容真实问卷星与模拟导出。"""
    cmap = {}
    for idx, h in enumerate(headers):
        n = qnum(h)
        if n is not None:
            cmap[n] = idx
    return cmap


def is_dropped(h):
    return any(k in h for k in DROP_META_COLS)


def pct(n, d):
    return f"{(100.0 * n / d):.1f}%" if d else "0.0%"


def write_table(name, header, data_rows):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data_rows)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="问卷星导出 CSV（或模拟数据 CSV）")
    args = ap.parse_args()
    if not os.path.exists(args.input):
        sys.exit(f"找不到输入文件：{args.input}")

    headers, rows = read_csv(args.input)
    cmap = build_colmap(headers)
    dropped = [h for h in headers if is_dropped(h)]

    # 模拟数据水印检测
    sim_idx = next((i for i, h in enumerate(headers) if "__数据性质__" in h), None)
    is_sim = sim_idx is not None and any(
        (len(r) > sim_idx and "模拟" in r[sim_idx]) for r in rows)

    q_by_num = {q[0]: q for q in QUESTIONS}

    def cell(r, num):
        i = cmap.get(num)
        return r[i].strip() if (i is not None and i < len(r)) else ""

    # 仅保留知情同意=同意 的有效答卷
    valid = [r for r in rows if cell(r, 1).startswith("同意")]
    # 按 Q2 分卷
    buckets = {"A": [], "B": [], "C": [], "D": []}
    role_map = {"科研人员": "A", "科研管理": "B", "财务": "C", "审计": "C", "其他": "D"}
    for r in valid:
        v2 = cell(r, 2)
        role = "D"
        for key, rl in role_map.items():
            if key in v2:
                role = rl
                break
        buckets[role].append(r)

    md = []
    W = "> ⚠️ **本摘要基于「测试用模拟数据」，非真实问卷结果，严禁写入课题报告。**\n" \
        if is_sim else ""
    md.append("# 问卷分析摘要\n")
    if W:
        md.append(W)
    md.append(f"- 输入文件：`{os.path.basename(args.input)}`")
    md.append(f"- 原始答卷：{len(rows)} 行；知情同意有效：{len(valid)} 行")
    if dropped:
        md.append(f"- 已去标识化删除列：{', '.join(dropped)}")
    else:
        md.append("- 去标识化：未发现 IP/来源/地区等可定位列（导出已干净或本就无）")

    # —— 回收量表 ——
    rec = [[ROLE_LABEL[k], len(buckets[k])] for k in ("A", "B", "C", "D")]
    rec.append(["合计(有效)", len(valid)])
    write_table("01_回收量.csv", ["分卷", "有效份数"], rec)
    md.append("\n## 一、回收情况\n")
    md.append("| 分卷 | 有效份数 |")
    md.append("|------|---------|")
    for a, b in rec:
        md.append(f"| {a} | {b} |")
    md.append("\n> 结题报告须写明：本院各类人群分母、发放数、回收数、回收率。"
              "小群体（管理/财务）人少时按近普查口径说明。")

    # —— 单选/多选频数 ——
    md.append("\n## 二、单选 / 多选 题频数（按适用人群）\n")
    for q in QUESTIONS:
        num, fld, typ, tr, stem, opts, mx = q
        if typ not in ("single", "multi"):
            continue
        pool = (valid if tr == "ALL"
                else buckets.get(tr, []))
        if not pool:
            continue
        counts = {}
        denom = 0
        for r in pool:
            v = cell(r, num)
            if not v:
                continue
            denom += 1
            if typ == "multi":
                for part in re.split(r"[┋,，、;；|]", v):
                    part = part.strip()
                    if part:
                        counts[part] = counts.get(part, 0) + 1
            else:
                counts[v] = counts.get(v, 0) + 1
        if denom == 0:
            continue
        rows_out = sorted(counts.items(), key=lambda x: -x[1])
        tbl = [[k, n, pct(n, denom)] for k, n in rows_out]
        write_table(f"Q{num:02d}_{fld}.csv",
                    ["选项", "计数", f"占比(分母={denom})"], tbl)
        md.append(f"\n**Q{num}. {stem}**（{ROLE_LABEL.get(tr,'全部') if tr!='ALL' else '全部'}，"
                  f"有效作答 {denom}{'，多选' if typ=='multi' else ''}）")
        for k, n in rows_out[:6]:
            md.append(f"- {k}：{n}（{pct(n, denom)}）")

    # —— 量表题统计 ——
    md.append("\n## 三、五级量表题（1=完全不符合 … 5=完全符合）\n")
    md.append("| 题号 | 题干 | 适用 | N | 均值 | 标准差 | 偏向 |")
    md.append("|------|------|------|---|------|--------|------|")
    scale_table = [["题号", "题干", "适用", "N", "均值", "标准差",
                    "完全不符合", "较不符合", "一般", "较符合", "完全符合"]]
    for q in QUESTIONS:
        num, fld, typ, tr, stem, opts, mx = q
        if typ != "scale":
            continue
        pool = valid if tr == "ALL" else buckets.get(tr, [])
        scores, dist = [], {s: 0 for s in SCALE}
        for r in pool:
            v = cell(r, num)
            if v in SCALE_SCORE:
                scores.append(SCALE_SCORE[v])
                dist[v] += 1
            elif v.isdigit() and 1 <= int(v) <= 5:
                scores.append(int(v))
                dist[SCALE[int(v) - 1]] += 1
        if not scores:
            continue
        mean = statistics.mean(scores)
        sd = statistics.pstdev(scores) if len(scores) > 1 else 0.0
        lean = "偏正面(认同)" if mean >= 3.4 else ("偏负面(不认同)" if mean <= 2.6 else "中性/分歧")
        md.append(f"| Q{num} | {stem[:22]} | {ROLE_LABEL.get(tr,'全部') if tr!='ALL' else '全部'} "
                  f"| {len(scores)} | {mean:.2f} | {sd:.2f} | {lean} |")
        scale_table.append([f"Q{num}", stem, tr, len(scores), f"{mean:.2f}", f"{sd:.2f}",
                            *[dist[s] for s in SCALE]])
    write_table("02_量表题统计.csv", scale_table[0], scale_table[1:])

    # —— 量表 × 职称 / 年限 交叉（仅通用量表题，样本足够才有意义）——
    def crosstab(group_q, title, fname):
        out = [["量表题"] ]
        # 组别取值
        gq = q_by_num[group_q]
        gopts = [lbl for _c, lbl in gq[5]]
        out[0] += gopts
        for q in QUESTIONS:
            num, fld, typ, tr, stem, *_ = q
            if typ != "scale" or tr != "ALL":
                continue
            row = [f"Q{num} {stem[:16]}"]
            for g in gopts:
                sc = []
                for r in valid:
                    if cell(r, group_q) == g and cell(r, num) in SCALE_SCORE:
                        sc.append(SCALE_SCORE[cell(r, num)])
                row.append(f"{statistics.mean(sc):.2f}(n={len(sc)})" if sc else "-")
            out.append(row)
        write_table(fname, out[0], out[1:])
        md.append(f"\n## 四、{title}（通用量表题均值，单元格=均值(n)）\n")
        md.append("| " + " | ".join(out[0]) + " |")
        md.append("|" + "|".join(["---"] * len(out[0])) + "|")
        for r in out[1:]:
            md.append("| " + " | ".join(str(x) for x in r) + " |")

    crosstab(3, "按职称/职级交叉", "03_量表x职称.csv")
    crosstab(4, "按工作年限交叉", "04_量表x年限.csv")

    md.append("\n---\n")
    md.append("**字段映射**：分析按问卷星表头前导题号（如 `6.`）匹配，"
              "真实导出表头题号不变即可直接复用本流水线。")
    if is_sim:
        md.append("\n> ⚠️ 再次提醒：以上全部基于模拟测试数据，仅用于验证分析流程与模板，"
                  "不得出现在《原创性声明》覆盖的任何课题成果中。")

    summary_path = os.path.join(OUT, "分析摘要.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print("=" * 56)
    if is_sim:
        print("  [!]  输入为【模拟测试数据】，结果仅供流程验证，勿入报告")
    print(f"  有效答卷 {len(valid)}：A={len(buckets['A'])} "
          f"B={len(buckets['B'])} C={len(buckets['C'])} D={len(buckets['D'])}")
    if dropped:
        print(f"  已去标识化删列：{dropped}")
    print(f"  统计表与《分析摘要.md》已写入：{OUT}")
    print("=" * 56)


if __name__ == "__main__":
    main()
