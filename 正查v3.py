#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正向神煞标注脚本 v8.2 - 多起法拆分标注，集合比较修复
完全对齐逆向引擎 v6.2，每个标签唯一对应引擎一个子规则
生成文件：shensha_60_plus_final_v8_2.txt
"""

# ==================== 基础常量 ====================
STEMS = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
BRANCHES = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

NAYIN_WUXING = [
    0,0,3,3,2,2,4,4,0,0,
    3,3,1,1,4,4,0,0,2,2,
    1,1,4,4,3,3,2,2,1,1,
    0,0,3,3,2,2,4,4,0,0,
    3,3,1,1,4,4,0,0,2,2,
    2,2,1,1,4,4,2,2,1,1
]

def gz_index(stem, branch):
    return (6 * stem - 5 * branch) % 60

def gz_split(index):
    return index % 10, index % 12

MONTH_STEM_BASE = [2,4,6,8,0, 2,4,6,8,0]
def month_stem(year_stem, month_branch):
    return (MONTH_STEM_BASE[year_stem] + (month_branch - 2) % 12) % 10

HOUR_STEM_BASE = [0,2,4,6,8, 0,2,4,6,8]
def hour_stem(day_stem, hour_branch):
    return (HOUR_STEM_BASE[day_stem] + hour_branch) % 10

# ==================== 辅助数据（与引擎完全一致） ====================
HEAVENLY_HE = {0:5, 1:6, 2:7, 3:8, 4:9, 5:0, 6:1, 7:2, 8:3, 9:4}
EARTHLY_HE = {0:1, 1:0, 2:11, 11:2, 3:10, 10:3, 4:9, 9:4, 5:8, 8:5, 6:7, 7:6}
WUXING_LIST = [2, 2, 3, 3, 4, 4, 0, 0, 1, 1]
def stems_ke(s1, s2):
    w1, w2 = WUXING_LIST[s1], WUXING_LIST[s2]
    return (w1==2 and w2==4) or (w1==3 and w2==0) or (w1==4 and w2==1) or (w1==0 and w2==2) or (w1==1 and w2==3)

# 固定集合
KUIGANG = {16,46,4,34,28,58}
LIUXIU = {42,43,24,54,25,55}
YINCHAYANGCUO = {27,28,29,42,43,44,57,58,59,12,13,14}
SHIEDABAI = {40,41,8,32,23,16,34,59,17,25}
BAZHUAN = {50,51,43,34,55,56,57,49,4,25}
JINSHEN_FIXED = {1,5,9}
SHILING = {40,11,52,33,54,46,26,47,38,19}
JIUCHOU = {48,18,24,54,45,15,21,51,57,27}
GULUAN = {41,53,47,44,50,42,54,48}

# 干→支映射（集合类型用于多值）
LU_MAP = {0:2,1:3,2:5,3:6,4:5,5:6,6:8,7:9,8:11,9:0}
JINYU_MAP = {0:4,1:5,2:7,3:8,4:7,5:8,6:10,7:11,8:1,9:2}
WENCHANG_MAP = {0:5,1:6,2:8,3:9,4:8,5:9,6:11,7:0,8:2,9:3}
FUXING_MAP = {0:{2,0},2:{2,0}, 1:{3,1},9:{3,1}, 4:{8},5:{7},3:{11},6:{6},7:{5},8:{4}}
TAIJI_MAP = {0:{0,6},1:{0,6}, 2:{3,9},3:{3,9}, 4:{4,10,1,7},5:{4,10,1,7}, 6:{2,11},7:{2,11}, 8:{5,8},9:{5,8}}
GUOYIN_MAP = {0:10,1:11,2:1,3:2,4:1,5:2,6:4,7:5,8:7,9:8}
HONGYAN_MAP = {0:6,1:8,2:2,3:7,4:4,5:4,6:10,7:9,8:0,9:8}
YANGREN_MAP = {0:3,1:2,2:6,4:6,3:5,5:5,6:9,7:8,8:0,9:11}
YANGREN_V2 = {0:3,1:4,2:6,3:7,4:6,5:7,6:9,7:10,8:0,9:1}
YANGREN_V3 = {0:3,2:6,4:6,6:9,8:0}
LIUXIA_MAP = {0:9,1:10,2:7,3:8,4:5,5:6,6:4,7:3,8:11,9:2}
TIANYI_MAP = {0:{1,7},4:{1,7}, 1:{0,8},5:{0,8}, 2:{11,9},3:{11,9}, 6:{2,6},7:{2,6}, 8:{3,5},9:{3,5}}
TIANYI_V3 = {0:{1,7},4:{1,7},6:{1,7}, 1:{0,8},5:{0,8}, 2:{11,9},3:{11,9}, 8:{5,3},9:{5,3}, 7:{2,6}}
TIANCHU_MAP = {0:{5},1:{6},2:{5},3:{6},4:{8}, 5:{9}, 6:{11},7:{0},8:{2},9:{3}}
CIGUAN_MAP = {0:26,1:27,2:41,3:54,4:53,5:6,6:8,7:9,8:59,9:58}
XUETANG_STEM = {0:{4,11},1:{5,6},2:{7,2},3:{8,9},4:{7,2},5:{8,9},6:{10,5},7:{11,0},8:{1,8},9:{2,3}}

# 支→支映射
PITOU_MAP = {0:4,1:3,2:2,3:1,4:10,5:11,6:10,7:9,8:8,9:7,10:6,11:5}
PIMA_MAP = {0:9,1:10,2:11,3:0,4:3,5:2,6:3,7:4,8:5,9:6,10:7,11:8}
HONGLUAN_MAP = {0:3,1:2,2:1,3:0,4:11,5:10,6:9,7:8,8:7,9:6,10:5,11:4}
TIANXI_MAP = {0:9,1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1,9:0,10:11,11:10}
XUEREN_MAP = {2:1,3:7,4:2,5:8,6:3,7:9,8:4,9:10,10:5,11:11,0:6,1:0}
ANJIN_MAP = {0:5,6:5,3:5,9:5, 2:9,8:9,5:9,11:9, 4:1,10:1,1:1,7:1}

def bingfu(b): return (b-1)%12
def sangmen(b): return (b+2)%12
def diaoke(b): return (b-2)%12
def goujiao_set(b): return {(b+3)%12,(b-3)%12}
def yuanchen_set(b): chong = (b+6)%12; return {(chong+1)%12,(chong-1)%12}

def sanhe(pivot):
    m = {}
    for k, v in pivot.items():
        for b in k: m[b] = v
    return m

TAOHUA_MAP = sanhe({(8,0,4):9, (2,6,10):3, (11,3,7):0, (5,9,1):6})
YIMA_MAP = sanhe({(8,0,4):2, (2,6,10):8, (5,9,1):11, (11,3,7):5})
HUAGAI_MAP = sanhe({(2,6,10):10, (8,0,4):4, (5,9,1):1, (11,3,7):7})
JIANGXING_MAP = sanhe({(2,6,10):6, (8,0,4):0, (5,9,1):9, (11,3,7):3})
WANGSHEN_MAP = sanhe({(8,0,4):11, (2,6,10):5, (11,3,7):2, (5,9,1):8})
JIESHA_MAP = sanhe({(8,0,4):5, (2,6,10):11, (11,3,7):8, (5,9,1):2})
ZAISHA_MAP = sanhe({(8,0,4):6, (2,6,10):0, (11,3,7):9, (5,9,1):3})
LIUE_MAP = sanhe({(2,6,10):9, (8,0,4):3, (5,9,1):0, (11,3,7):6})
JINGUI_MAP = sanhe({(8,0,4):0, (11,3,7):3, (2,6,10):6, (5,9,1):9})
GUCHEN_MAP = {2:5,3:5,4:5,5:8,6:8,7:8,8:11,9:11,10:11,11:2,0:2,1:2}
GUASU_MAP = {2:1,3:1,4:1,5:4,6:4,7:4,8:7,9:7,10:7,11:10,0:10,1:10}

SIFEI_MAP = {2:{26,27},3:{26,27},4:{26,27},5:{48,59},6:{48,59},7:{48,59},
             8:{50,51},9:{50,51},10:{50,51},11:{42,53},0:{42,53},1:{42,53}}

def dexiu_set(mb):
    if mb in (2,6,10): return {2,3,4,9}
    if mb in (8,0,4): return {8,9,4,5,2,7,0,5}
    if mb in (5,9,1): return {6,7,1,6}
    if mb in (11,3,7): return {0,1,3,8}
    return set()

SEASON_HOUR_MAP = {2:{2,0},3:{2,0},4:{2,0},5:{3,7},6:{3,7},7:{3,7},
                   8:{5,8},9:{5,8},10:{5,8},11:{6,9},0:{6,9},1:{6,9}}
NAYIN_B_MAP = {0:{6,3},2:{6,3},1:{9,10},3:{9,10},4:{4,5}}
NAYIN_S_MAP = {0:{0,1},2:{2,3},1:{4,5},3:{6,7},4:{8,9}}
JINSHEN_COMB = {(1,1),(5,5),(9,9)}

# ==================== 检查函数（拆分标注） ====================
def check_all(b):
    ys, yb = b['ys'], b['yb']
    ms, mb = b['ms'], b['mb']
    ds, db = b['ds'], b['db']
    hs, hb = b['hs'], b['hb']
    y_idx = gz_index(ys, yb)
    d_idx = gz_index(ds, db)
    h_idx = gz_index(hs, hb)
    y_wx = NAYIN_WUXING[y_idx]
    res = []

    def add(msg): res.append(msg)

    # 固定日柱
    if d_idx in KUIGANG: add("魁罡(日柱)")
    if d_idx in LIUXIU: add("六秀(日柱)")
    if d_idx in YINCHAYANGCUO: add("阴差阳错(日柱)")
    if d_idx in SHIEDABAI: add("十恶大败(日柱)")
    if d_idx in BAZHUAN: add("八专(日柱)")
    if d_idx in JINSHEN_FIXED: add("金神(日柱)")
    if h_idx in JINSHEN_FIXED: add("金神(时柱)")
    if (ds, hb) in JINSHEN_COMB: add("金神(时柱)")
    if d_idx in SHILING: add("十灵(日柱)")
    if h_idx in SHILING: add("十灵(时柱)")
    if d_idx in JIUCHOU: add("九丑(日柱)")
    if d_idx in GULUAN:
        add("孤鸾(日柱)")
        if h_idx in GULUAN: add("孤鸾(时柱)")
    if d_idx in {23,39} and hb in {3,4,5,6,7,8}: add("日贵(时柱)")

    pillars = [("年柱",ys,yb),("月柱",ms,mb),("日柱",ds,db),("时柱",hs,hb)]

    for p, s, br in pillars:
        # 禄神 (只有日干起法)
        if br == LU_MAP.get(ds):
            add(f"禄神({p})")
        # 金舆
        if br == JINYU_MAP.get(ds): add(f"金舆(日干,{p})")
        if br == JINYU_MAP.get(ys): add(f"金舆(年干,{p})")
        # 阳刃（三种口诀拆分）
        if br == YANGREN_MAP.get(ds): add(f"阳刃(口诀1,{p})")
        if br == YANGREN_V2.get(ds): add(f"阳刃(口诀2,{p})")
        if br == YANGREN_V3.get(ds): add(f"阳刃(口诀3,{p})")
        # 飞刃（基于口诀1）
        if YANGREN_MAP.get(ds) is not None and br == (YANGREN_MAP[ds] + 6) % 12:
            add(f"飞刃({p})")
        # 文昌
        if br == WENCHANG_MAP.get(ds): add(f"文昌(日干,{p})")
        if br == WENCHANG_MAP.get(ys): add(f"文昌(年干,{p})")
        # 福星贵人（修复：使用 in 检查集合，拆分选项）
        if br in FUXING_MAP.get(ds, set()): add(f"福星贵人(日干,{p})")
        if br in FUXING_MAP.get(ys, set()): add(f"福星贵人(年干,{p})")
        # 太极贵人
        if br in TAIJI_MAP.get(ds, set()): add(f"太极贵人(日干,{p})")
        if br in TAIJI_MAP.get(ys, set()): add(f"太极贵人(年干,{p})")
        # 国印贵人
        if br == GUOYIN_MAP.get(ds): add(f"国印贵人(日干,{p})")
        if br == GUOYIN_MAP.get(ys): add(f"国印贵人(年干,{p})")
        # 天乙贵人（口诀拆分）
        if br in TIANYI_MAP.get(ds, set()): add(f"天乙贵人(口诀1日干,{p})")
        if br in TIANYI_MAP.get(ys, set()): add(f"天乙贵人(口诀1年干,{p})")
        if br in TIANYI_V3.get(ds, set()): add(f"天乙贵人(口诀3日干,{p})")
        if br in TIANYI_V3.get(ys, set()): add(f"天乙贵人(口诀3年干,{p})")
        # 红艳
        if br == HONGYAN_MAP.get(ds): add(f"红艳(日干,{p})")
        if br == HONGYAN_MAP.get(ys): add(f"红艳(年干,{p})")
        # 流霞（只有日干）
        if br == LIUXIA_MAP.get(ds): add(f"流霞({p})")
        # 天厨
        if br in TIANCHU_MAP.get(ds, set()): add(f"天厨(日干,{p})")
        if br in TIANCHU_MAP.get(ys, set()): add(f"天厨(年干,{p})")

        # 年支起的神煞
        if br == PITOU_MAP.get(yb): add(f"披头(年支,{p})")
        if br == PIMA_MAP.get(yb): add(f"披麻(年支,{p})")
        if br == HONGLUAN_MAP.get(yb): add(f"红鸾(年支,{p})")
        if br == TIANXI_MAP.get(yb): add(f"天喜(年支,{p})")
        if br == sangmen(yb): add(f"丧门(年支,{p})")
        if br == diaoke(yb): add(f"吊客(年支,{p})")
        if br == bingfu(yb): add(f"病符(年支,{p})")
        if br in goujiao_set(yb): add(f"钩绞(年支,{p})")

        # 年/日支起的神煞
        if br == TAOHUA_MAP.get(yb): add(f"桃花(年支,{p})")
        if br == TAOHUA_MAP.get(db): add(f"桃花(日支,{p})")
        if br == YIMA_MAP.get(yb): add(f"驿马(年支,{p})")
        if br == YIMA_MAP.get(db): add(f"驿马(日支,{p})")
        if br == HUAGAI_MAP.get(yb): add(f"华盖(年支,{p})")
        if br == HUAGAI_MAP.get(db): add(f"华盖(日支,{p})")
        if br == JIANGXING_MAP.get(yb): add(f"将星(年支,{p})")
        if br == JIANGXING_MAP.get(db): add(f"将星(日支,{p})")
        if br == WANGSHEN_MAP.get(yb): add(f"亡神(年支,{p})")
        if br == WANGSHEN_MAP.get(db): add(f"亡神(日支,{p})")
        if br == JIESHA_MAP.get(yb): add(f"劫煞(年支,{p})")
        if br == JIESHA_MAP.get(db): add(f"劫煞(日支,{p})")

        # 年支独用
        if br == ZAISHA_MAP.get(yb): add(f"灾煞(年支,{p})")
        if br == LIUE_MAP.get(yb): add(f"六厄(年支,{p})")
        if br == JINGUI_MAP.get(yb): add(f"金匮(年支,{p})")

        # 孤辰/寡宿
        if br == GUCHEN_MAP.get(yb): add(f"孤辰(年支,{p})")
        if br == GUCHEN_MAP.get(db): add(f"孤辰(日支,{p})")
        if br == GUASU_MAP.get(yb): add(f"寡宿(年支,{p})")
        if br == GUASU_MAP.get(db): add(f"寡宿(日支,{p})")

        # 月支起
        if br == XUEREN_MAP.get(mb): add(f"血刃(月支,{p})")
        if br == (mb-1)%12: add(f"天医(月支,{p})")
        # 暗金（时柱，年支）
        if p == "时柱" and br == ANJIN_MAP.get(yb): add("暗金(年支,时柱)")

    # 词馆（拆分标注，并保留合并标签）
    ci = {2:2,3:5,4:11,0:8,1:11}
    ci_target = {2:26,3:41,0:8}
    for p, s, br in pillars:
        idx = gz_index(s, br)
        if idx == CIGUAN_MAP.get(ds): add(f"词馆(日干->柱,{p})")
        if idx == CIGUAN_MAP.get(ys): add(f"词馆(年干->柱,{p})")
        if br == ci.get(y_wx): add(f"词馆(纳音支,{p})")
        if idx == ci_target.get(y_wx): add(f"词馆(纳音临官,{p})")
        if any(t.startswith("词馆(") and t.endswith(f",{p})") for t in res):
            add(f"词馆({p})")

    # 学堂（拆分 + 合并）
    cs = {2:11,3:2,4:8,0:5,1:8}
    xt_target = {4:23, 1:59}
    for p, s, br in pillars:
        if br == cs.get(y_wx): add(f"学堂(学堂纳音,{p})")
        if br in XUETANG_STEM.get(ds, set()): add(f"学堂(学堂日干,{p})")
        if gz_index(s, br) == xt_target.get(y_wx): add(f"学堂(学堂同临官,{p})")
        if any(t.startswith("学堂(") and t.endswith(f",{p})") for t in res):
            add(f"学堂({p})")

    # 天赦
    ts = {2:{14},3:{14},4:{14},5:{30},6:{30},7:{30},8:{44},9:{44},10:{44},11:{0},0:{0},1:{0}}
    if mb in ts and d_idx in ts[mb]: add("天赦(日柱)")

    # 天德、天德合
    td = {2:{"stem":3},3:{"branch":8},4:{"stem":8},5:{"stem":7},6:{"branch":11},7:{"stem":0},
          8:{"stem":9},9:{"branch":2},10:{"stem":2},11:{"stem":1},0:{"branch":5},1:{"stem":6}}
    if mb in td:
        c = td[mb]
        if "stem" in c:
            for p, s, _ in pillars:
                if s == c["stem"]: add(f"天德({p})")
            he_s = HEAVENLY_HE[c["stem"]]
            for p, s, _ in pillars:
                if s == he_s: add(f"天德合({p})")
        else:
            for p, _, br in pillars:
                if br == c["branch"]: add(f"天德({p})")
            he_b = EARTHLY_HE[c["branch"]]
            for p, _, br in pillars:
                if br == he_b: add(f"天德合({p})")

    # 月德、月德合
    yd = {8:8,0:8,4:8,11:0,3:0,7:0,2:2,6:2,10:2,5:6,9:6,1:6}
    if mb in yd:
        for p, s, _ in pillars:
            if s == yd[mb]: add(f"月德({p})")
        he_s = HEAVENLY_HE[yd[mb]]
        for p, s, _ in pillars:
            if s == he_s: add(f"月德合({p})")

    # 天罗、地网
    if y_wx == 3 and db in {10,11}: add("天罗(日柱)")
    if y_wx in (1,4) and db in {4,5}: add("地网(日柱)")
    if any(t.startswith("天罗(") or t.startswith("地网(") for t in res):
        add("天罗地网(日柱)")

    # 夜贵
    if d_idx in {29,33} and hb in {9,10,11,0,1,2}: add("夜贵(时柱)")

    # 反吟
    for p, s, br in pillars:
        if p == "日柱": continue
        if s == ds and br == (db + 6) % 12: add(f"反吟({p})")
        elif br == EARTHLY_HE.get(db) and stems_ke(s, ds): add(f"反吟({p})")

    # 元辰
    for p, _, br in pillars:
        if br in yuanchen_set(db): add(f"元辰(日支,{p})")
        if br in yuanchen_set(yb): add(f"元辰(年支,{p})")

    # 三奇
    seq1 = (ys, ms, ds)
    seq2 = (ms, ds, hs)
    valid_seqs = [(0,4,6), (1,2,3), (8,9,7)]
    if seq1 in valid_seqs or seq2 in valid_seqs: add("三奇贵人(全局)")

    # 四废
    if mb in SIFEI_MAP and d_idx in SIFEI_MAP[mb]: add("四废(日柱)")

    # 六甲空亡
    yang = sum(1 for s, br in [(ys,yb),(ms,mb),(ds,db),(hs,hb)] if s%2==0) + \
           sum(1 for s, br in [(ys,yb),(ms,mb),(ds,db),(hs,hb)] if br%2==0)
    yin = 8 - yang
    if (ds%2==0 and yang > yin) or (ds%2!=0 and yang < yin): add("六甲空亡(日柱)")

    # 空亡
    xun = d_idx - (d_idx % 10)
    kong = {(xun%12+10)%12, (xun%12+11)%12}
    for p, _, br in pillars:
        if br in kong: add(f"空亡({p})")

    # 童子
    if mb in SEASON_HOUR_MAP and hb in SEASON_HOUR_MAP[mb]: add("童子(时柱)")
    if y_wx in NAYIN_B_MAP:
        if db in NAYIN_B_MAP[y_wx]: add("童子(日柱)")
        if hb in NAYIN_B_MAP[y_wx]: add("童子(时柱)")
    if y_wx in NAYIN_S_MAP:
        if ds in NAYIN_S_MAP[y_wx]: add("童子(日柱)")
        if hs in NAYIN_S_MAP[y_wx]: add("童子(时柱)")

    # 德秀
    ds_set = dexiu_set(mb)
    for p, s, _ in pillars:
        if s in ds_set: add(f"德秀贵人(月令,{p})")

    # 去重
    seen = set()
    unique = []
    for r in res:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique

# ==================== 主程序 ====================
def main():
    out = "shensha_60_plus_final_v8_2.txt"
    total = 518400
    cnt = 0
    print("开始生成 v8.2 正向数据（拆分多起法标签，修复集合比较）...")
    with open(out, "w", encoding="utf-8") as f:
        f.write("八字\t神煞列表\n")
        for yi in range(60):
            ys, yb = gz_split(yi)
            for mb in range(12):
                ms = month_stem(ys, mb)
                if ms%2 != mb%2: continue
                for di in range(60):
                    ds, db = gz_split(di)
                    for hb in range(12):
                        hs = hour_stem(ds, hb)
                        if hs%2 != hb%2: continue
                        bazi = (STEMS[ys]+BRANCHES[yb] + " " +
                                STEMS[ms]+BRANCHES[mb] + " " +
                                STEMS[ds]+BRANCHES[db] + " " +
                                STEMS[hs]+BRANCHES[hb])
                        cand = {"ys":ys,"yb":yb,"ms":ms,"mb":mb,"ds":ds,"db":db,"hs":hs,"hb":hb}
                        lst = check_all(cand)
                        f.write(bazi + "\t" + "，".join(lst) + "\n")
                        cnt += 1
                        if cnt % 20000 == 0:
                            print(f"{cnt}/{total} ({100*cnt/total:.1f}%)")
    print(f"完成，共 {cnt} 条，保存至 {out}")

if __name__ == "__main__":
    main()