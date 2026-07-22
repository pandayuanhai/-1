#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正向数据集验证逆向引擎：严格模式下的召回率与唯一率（全输出版）
依赖：神煞倒查八字备份版5.py（v6.0），shensha_60_plus_final_v8.txt
修改：不再限制未召回打印数量，所有问题八字均输出
"""

import sys, re, time, importlib, os, traceback

try:
    engine = importlib.import_module("神煞倒查八字")
except ImportError:
    print("错误：找不到神煞倒查八字.py")
    sys.exit(1)

ConstraintSolver = engine.ConstraintSolver
parse_condition = engine.parse_condition
RULE_GENERATORS = engine.RULE_GENERATORS

# ==================== 配置 ====================
FORWARD_FILE = "shensha_60_plus_final_v8_2.txt"
PROGRESS_FILE = "progress_strict.txt"
SKIP_FILE = "skip_strict.txt"
ERROR_LOG = "error_strict.log"
BATCH_SIZE = 500
MAX_COMPLETION = 10000

# ==================== 文件操作 ====================
def load_set_from_file(filename):
    if not os.path.exists(filename): return set()
    with open(filename, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def append_line_to_file(filename, line):
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

def read_start_line():
    if not os.path.exists(PROGRESS_FILE): return 0
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        try: return int(f.read().strip())
        except: return 0

def write_start_line(line_num):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        f.write(str(line_num))

def iter_forward_data(filename, start_line=0, skip_set=None):
    if skip_set is None: skip_set = set()
    with open(filename, 'r', encoding='utf-8') as f:
        f.readline()
        for _ in range(start_line): f.readline()
        for line in f:
            line = line.strip()
            if not line or '\t' not in line: continue
            parts = line.split('\t')
            if len(parts) < 2: continue
            bazi = parts[0]
            if bazi in skip_set: continue
            shensha_list = [s.strip() for s in parts[1].split('，') if s.strip()]
            yield bazi, shensha_list

def parse_shensha_label(label):
    """正确解析 v8.2 标签，例如 '福星贵人(日干,年柱)' -> ('福星贵人', '日干', '年柱')"""
    m = re.match(r'^(.+?)\((.+?)\)$', label)
    if not m:
        return None
    shensha = m.group(1)
    content = m.group(2)
    pillar_kw = {"年柱","月柱","日柱","时柱","全局"}
    # 先处理带选项的格式：选项,柱位
    if ',' in content:
        # 从右侧分割，因为选项可能包含逗号（如'日干->柱'）
        parts = content.rsplit(',', 1)
        if len(parts) == 2 and parts[1].strip() in pillar_kw:
            option = parts[0].strip()
            pillar = parts[1].strip()
            return (shensha, option, pillar)
    # 再处理直接柱位格式：神煞名(柱位)
    if content in pillar_kw:
        return (shensha, None, content)
    return None

def shensha_to_conditions(labels):
    conds = []
    for lb in labels:
        parsed = parse_shensha_label(lb)
        if not parsed:
            continue
        shensha, option, pillar = parsed
        if pillar == "全局":
            pillar = "日柱"   # 统一转为日柱
        if option:
            cond = f"{pillar}{shensha}({option})"
        else:
            cond = f"{pillar}{shensha}"
        conds.append(cond)
    return conds

def format_candidate(cand):
    stem_list = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
    branch_list = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
    def fmt(s, b):
        if s is None and b is None: return "??"
        s_str = stem_list[s] if s is not None else "?"
        b_str = branch_list[b] if b is not None else "?"
        return s_str + b_str
    return (f"{fmt(cand['year_stem'],cand['year_branch'])} "
            f"{fmt(cand['month_stem'],cand['month_branch'])} "
            f"{fmt(cand['day_stem'],cand['day_branch'])} "
            f"{fmt(cand['hour_stem'],cand['hour_branch'])}")

# ==================== 单批验证 ====================
def validate_batch(batch, stats, skip_set):
    for bazi_str, shen_list in batch:
        conditions = shensha_to_conditions(shen_list)
        if not conditions:
            continue
        stats['valid_total'] += 1

        solver = ConstraintSolver()
        for cond in conditions:
            try:
                pillar, shen, option = parse_condition(cond)
                gen = RULE_GENERATORS[shen]
                rule = gen(pillar, option) if callable(gen) else gen
                solver.add_rule(rule, pillar, shen)
            except Exception as e:
                # 条件解析失败，输出并记录
                print(f"  ⚠️ 条件解析失败：{cond} | 八字：{bazi_str} | 异常：{e}")
                continue

        # 求解
        try:
            results = solver.solve(strict=True, max_completion=MAX_COMPLETION)
        except Exception as e:
            print(f"  ❌ 求解异常：{bazi_str} | {e}")
            traceback.print_exc()
            append_line_to_file(ERROR_LOG, f"{bazi_str}\t{shen_list}\t{str(e)}")
            append_line_to_file(SKIP_FILE, bazi_str)
            skip_set.add(bazi_str)
            continue

        cand_strs = [format_candidate(c) for c in results]

        if bazi_str in cand_strs:
            stats['recall'] += 1
        else:
            # 无条件打印所有未召回
            print(f"  🚫 未召回：{bazi_str} | 神煞数：{len(shen_list)} | 候选数：{len(cand_strs)}")
            stats['not_found'] += 1

        if len(cand_strs) == 1 and cand_strs[0] == bazi_str:
            stats['exact_match'] += 1

        stats['candidate_sizes'].append(len(cand_strs))

# ==================== 主程序 ====================
def main():
    skip_set = load_set_from_file(SKIP_FILE)
    print(f"已加载严格模式黑名单：{len(skip_set)} 条")

    start_line = read_start_line()
    print(f"从第 {start_line} 行之后开始（已处理 {start_line} 条）")

    stats = {'valid_total': 0, 'recall': 0, 'exact_match': 0, 'candidate_sizes': [], 'not_found': 0}
    batch = []
    total_processed = start_line
    start_time = time.time()

    print("开始严格模式验证（无限输出未召回）...")
    for bazi_str, shen_list in iter_forward_data(FORWARD_FILE, start_line=start_line, skip_set=skip_set):
        batch.append((bazi_str, shen_list))
        if len(batch) >= BATCH_SIZE:
            validate_batch(batch, stats, skip_set)
            total_processed += len(batch)
            write_start_line(total_processed)
            elapsed = time.time() - start_time
            recall_rate = stats['recall'] / stats['valid_total'] * 100 if stats['valid_total'] > 0 else 0
            exact_rate = stats['exact_match'] / stats['valid_total'] * 100 if stats['valid_total'] > 0 else 0
            print(f"已处理 {total_processed} 条 | "
                  f"召回率: {stats['recall']}/{stats['valid_total']} = {recall_rate:.2f}% | "
                  f"唯一率: {stats['exact_match']}/{stats['valid_total']} = {exact_rate:.2f}% | "
                  f"耗时 {elapsed:.1f}s")
            batch = []

    if batch:
        validate_batch(batch, stats, skip_set)
        total_processed += len(batch)
        write_start_line(total_processed)

    print("\n========== 验证完成 ==========")
    print(f"总处理样本数: {total_processed}")
    print(f"有效样本数: {stats['valid_total']}")
    if stats['valid_total'] > 0:
        print(f"召回率: {stats['recall']}/{stats['valid_total']} = {stats['recall']/stats['valid_total']*100:.2f}%")
        print(f"唯一率: {stats['exact_match']}/{stats['valid_total']} = {stats['exact_match']/stats['valid_total']*100:.2f}%")
        avg = sum(stats['candidate_sizes']) / len(stats['candidate_sizes'])
        print(f"平均候选数: {avg:.2f}，最大: {max(stats['candidate_sizes'])}，最小: {min(stats['candidate_sizes'])}")
    print(f"未召回总数: {stats['not_found']}")
    print(f"总耗时: {time.time() - start_time:.2f} 秒")

if __name__ == "__main__":
    main()