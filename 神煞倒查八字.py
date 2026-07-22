#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字逆向推理引擎 v6.2 - 选项支持 + 修复合并标签行为
完全对齐正向标注 v8.1（需配合修正后的正向脚本）
"""
import re, gc

# ---------- 基础常量 ----------
STEMS = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
BRANCHES = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
NAYIN_WUXING = [
    0,0,3,3,2,2,4,4,0,0,3,3,1,1,4,4,0,0,2,2,
    1,1,4,4,3,3,2,2,1,1,0,0,3,3,2,2,4,4,0,0,
    3,3,1,1,4,4,0,0,2,2,2,2,1,1,4,4,2,2,1,1
]
def gz_index(s,b): return (6*s - 5*b) % 60
def gz_split(i): return i%10, i%12
MONTH_STEM_BASE = [2,4,6,8,0,2,4,6,8,0]
def month_stem(ys,mb): return (MONTH_STEM_BASE[ys] + (mb-2)%12)%10
HOUR_STEM_BASE = [0,2,4,6,8,0,2,4,6,8]
def hour_stem(ds,hb): return (HOUR_STEM_BASE[ds] + hb)%10

def empty_candidate():
    return {"year_stem":None,"year_branch":None,"month_stem":None,"month_branch":None,
            "day_stem":None,"day_branch":None,"hour_stem":None,"hour_branch":None}

def candidate_tuple(c):
    return (c["year_stem"],c["year_branch"],c["month_stem"],c["month_branch"],
            c["day_stem"],c["day_branch"],c["hour_stem"],c["hour_branch"])

def deduplicate(candidates):
    seen = set(); res = []
    for c in candidates:
        t = candidate_tuple(c)
        if t not in seen: seen.add(t); res.append(c)
    return res

# ---------- 规则构造器 ----------
def make_fixed_set_rule(indices, sk, bk):
    def rule(cand,tp=None):
        s=cand.get(sk); b=cand.get(bk)
        if s is not None and b is not None: return [cand] if gz_index(s,b) in indices else []
        if s is not None and b is None:
            return [{**cand,bk:b2} for b2 in range(12) if gz_index(s,b2) in indices]
        if s is None and b is not None:
            return [{**cand,sk:s2} for s2 in range(10) if gz_index(s2,b) in indices]
        return [{**cand,sk:i%10,bk:i%12} for i in indices]
    return rule

def branch_cross_stem_to_branch(cand, stem_k, branch_k, mapping):
    s=cand.get(stem_k); b=cand.get(branch_k)
    if s is not None and b is not None:
        t=mapping.get(s)
        if t is None or (isinstance(t,set) and len(t)==0): return []
        return [cand] if (isinstance(t,set) and b in t) or (not isinstance(t,set) and b==t) else []
    if s is not None and b is None:
        t=mapping.get(s)
        if t is None or (isinstance(t,set) and len(t)==0): return []
        return [{**cand,branch_k:v} for v in (t if isinstance(t,set) else [t])]
    if s is None and b is not None:
        res=[]
        for stem,val in mapping.items():
            if isinstance(val,set):
                if b in val: res.append({**cand,stem_k:stem})
            else:
                if b==val: res.append({**cand,stem_k:stem})
        return res
    res=[]
    for stem,val in mapping.items():
        for v in (val if isinstance(val,set) else [val]):
            res.append({**cand,stem_k:stem,branch_k:v})
    return res

def branch_cross_branch_to_branch(cand, src_b, tgt_b, mapping):
    sb=cand.get(src_b); tb=cand.get(tgt_b)
    if callable(mapping): mapping={b:mapping(b) for b in range(12)}
    if sb is not None and tb is not None:
        t=mapping.get(sb)
        if t is None: return []
        return [cand] if (isinstance(t,set) and tb in t) or (not isinstance(t,set) and tb==t) else []
    if sb is not None and tb is None:
        t=mapping.get(sb)
        if t is None: return []
        return [{**cand,tgt_b:v} for v in (t if isinstance(t,set) else [t])]
    if sb is None and tb is not None:
        res=[]
        for src,val in mapping.items():
            if isinstance(val,set):
                if tb in val: res.append({**cand,src_b:src})
            else:
                if tb==val: res.append({**cand,src_b:src})
        return res
    res=[]
    for src,val in mapping.items():
        for v in (val if isinstance(val,set) else [val]):
            res.append({**cand,src_b:src,tgt_b:v})
    return res

def make_rule_from_method(method, target_pillar):
    sk = method.get("source_kind")
    tk = method.get("target_kind")
    if sk=="none":
        return make_fixed_set_rule(method["fixed_pillars"], f"{target_pillar}_stem", f"{target_pillar}_branch")
    tgt_key = method["target_key_template"].format(pillar=target_pillar)
    mapping = method["mapping"]
    if sk=="stem" and tk=="branch":
        return lambda cand,tp=None: branch_cross_stem_to_branch(cand, method["source_key"], tgt_key, mapping)
    if sk=="branch" and tk=="branch":
        return lambda cand,tp=None: branch_cross_branch_to_branch(cand, method["source_key"], tgt_key, mapping)
    if sk=="stem" and tk=="pillar":
        def rule(cand,tp=None):
            src=cand.get(method["source_key"])
            if src is None: return [cand]
            idx=mapping.get(src)
            if idx is None: return []
            es,eb = gz_split(idx)
            cs=cand.get(target_pillar+"_stem"); cb=cand.get(target_pillar+"_branch")
            if cs is not None and cb is not None:
                return [cand] if gz_index(cs,cb)==idx else []
            elif cs is not None and cb is None:
                if cs!=es: return []
                return [{**cand, target_pillar+"_branch":eb}]
            elif cs is None and cb is not None:
                if cb!=eb: return []
                return [{**cand, target_pillar+"_stem":es}]
            else:
                return [{**cand, target_pillar+"_stem":es, target_pillar+"_branch":eb}]
        return rule
    if sk=="nayin_wuxing" and tk=="branch":
        def rule(cand,tp=None):
            prefix=method["source_key"]
            s=cand.get(prefix+"_stem"); b=cand.get(prefix+"_branch")
            if s is None or b is None: return [cand]
            wx=NAYIN_WUXING[gz_index(s,b)]
            tgt=mapping.get(wx)
            if tgt is None: return []
            cur=cand.get(tgt_key)
            if cur is not None: return [cand] if cur==tgt else []
            return [{**cand, tgt_key:tgt}]
        return rule
    if sk=="nayin_wuxing" and tk=="pillar":
        def rule(cand,tp=None):
            prefix=method["source_key"]
            s=cand.get(prefix+"_stem"); b=cand.get(prefix+"_branch")
            if s is None or b is None: return [cand]
            wx=NAYIN_WUXING[gz_index(s,b)]
            idx=mapping.get(wx)
            if idx is None: return []
            es,eb = gz_split(idx)
            cs=cand.get(target_pillar+"_stem"); cb=cand.get(target_pillar+"_branch")
            if cs is not None and cb is not None:
                return [cand] if gz_index(cs,cb)==idx else []
            elif cs is not None and cb is None:
                if cs!=es: return []
                return [{**cand, target_pillar+"_branch":eb}]
            elif cs is None and cb is not None:
                if cb!=eb: return []
                return [{**cand, target_pillar+"_stem":es}]
            else:
                return [{**cand, target_pillar+"_stem":es, target_pillar+"_branch":eb}]
        return rule
    raise NotImplementedError

def make_multi_method_rule(methods, pillar):
    rules = [make_rule_from_method(m, pillar) for m in methods]
    if len(rules)==1: return rules[0]
    def combined(cand,tp=None):
        res=[]
        for r in rules: res.extend(r(cand))
        return res
    return combined

# ---------- 神煞数据 ----------
HEAVENLY_HE = {0:5,1:6,2:7,3:8,4:9,5:0,6:1,7:2,8:3,9:4}
EARTHLY_HE = {0:1,1:0,2:11,11:2,3:10,10:3,4:9,9:4,5:8,8:5,6:7,7:6}
WUXING_LIST = [2,2,3,3,4,4,0,0,1,1]
def stems_ke(s1,s2):
    w1,w2 = WUXING_LIST[s1],WUXING_LIST[s2]
    return (w1==2 and w2==4) or (w1==3 and w2==0) or (w1==4 and w2==1) or (w1==0 and w2==2) or (w1==1 and w2==3)

# 固定集合
KUIGANG = {16,46,4,34,28,58}
LIUXIU = {42,43,24,54,25,55}
YINCHAYANGCUO = {27,28,29,42,43,44,57,58,59,12,13,14}
SHIEDABAI = {40,41,8,32,23,16,34,59,17,25}
BAZHUAN = {50,51,43,34,55,56,57,49,4,25}
JINSHEN = {1,5,9}
SHILING = {40,11,52,33,54,46,26,47,38,19}
JIUCHOU = {48,18,24,54,45,15,21,51,57,27}
GULUAN = {41,53,47,44,50,42,54,48}

# 映射表
LU_MAP = {0:2,1:3,2:5,3:6,4:5,5:6,6:8,7:9,8:11,9:0}
JINYU_MAP = {0:4,1:5,2:7,3:8,4:7,5:8,6:10,7:11,8:1,9:2}
WENCHANG_MAP = {0:5,1:6,2:8,3:9,4:8,5:9,6:11,7:0,8:2,9:3}
FUXING_MAP = {0:{2,0},2:{2,0},1:{3,1},9:{3,1},4:{8},5:{7},3:{11},6:{6},7:{5},8:{4}}
TAIJI_MAP = {0:{0,6},1:{0,6},2:{3,9},3:{3,9},4:{4,10,1,7},5:{4,10,1,7},6:{2,11},7:{2,11},8:{5,8},9:{5,8}}
GUOYIN_MAP = {0:10,1:11,2:1,3:2,4:1,5:2,6:4,7:5,8:7,9:8}
HONGYAN_MAP = {0:6,1:8,2:2,3:7,4:4,5:4,6:10,7:9,8:0,9:8}
YANGREN_MAP = {0:3,1:2,2:6,4:6,3:5,5:5,6:9,7:8,8:0,9:11}
YANGREN_V2 = {0:3,1:4,2:6,3:7,4:6,5:7,6:9,7:10,8:0,9:1}
YANGREN_V3 = {0:3,2:6,4:6,6:9,8:0}
LIUXIA_MAP = {0:9,1:10,2:7,3:8,4:5,5:6,6:4,7:3,8:11,9:2}
TIANYI_MAP = {0:{1,7},4:{1,7},1:{0,8},5:{0,8},2:{11,9},3:{11,9},6:{2,6},7:{2,6},8:{3,5},9:{3,5}}
TIANYI_V3 = {0:{1,7},4:{1,7},6:{1,7},1:{0,8},5:{0,8},2:{11,9},3:{11,9},8:{5,3},9:{5,3},7:{2,6}}
TIANCHU_MAP = {0:{5},1:{6},2:{5},3:{6},4:{8},5:{9},6:{11},7:{0},8:{2},9:{3}}
CIGUAN_MAP = {0:26,1:27,2:41,3:54,4:53,5:6,6:8,7:9,8:59,9:58}
XUETANG_STEM = {0:{4,11},1:{5,6},2:{7,2},3:{8,9},4:{7,2},5:{8,9},6:{10,5},7:{11,0},8:{1,8},9:{2,3}}

PITOU_MAP = {0:4,1:3,2:2,3:1,4:10,5:11,6:10,7:9,8:8,9:7,10:6,11:5}
PIMA_MAP = {0:9,1:10,2:11,3:0,4:3,5:2,6:3,7:4,8:5,9:6,10:7,11:8}
HONGLUAN_MAP = {0:3,1:2,2:1,3:0,4:11,5:10,6:9,7:8,8:7,9:6,10:5,11:4}
TIANXI_MAP = {0:9,1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1,9:0,10:11,11:10}
XUEREN_MAP = {2:1,3:7,4:2,5:8,6:3,7:9,8:4,9:10,10:5,11:11,0:6,1:0}
ANJIN_MAP = {0:5,6:5,3:5,9:5,2:9,8:9,5:9,11:9,4:1,10:1,1:1,7:1}
def bingfu(b): return (b-1)%12
def sangmen(b): return (b+2)%12
def diaoke(b): return (b-2)%12
def goujiao(b): return {(b+3)%12,(b-3)%12}
def yuanchen(b): c=(b+6)%12; return {(c+1)%12,(c-1)%12}
def sanhe(pivot):
    m={}
    for k,v in pivot.items():
        for b in k: m[b]=v
    return m
TAOHUA_MAP = sanhe({(8,0,4):9,(2,6,10):3,(11,3,7):0,(5,9,1):6})
YIMA_MAP = sanhe({(8,0,4):2,(2,6,10):8,(5,9,1):11,(11,3,7):5})
HUAGAI_MAP = sanhe({(2,6,10):10,(8,0,4):4,(5,9,1):1,(11,3,7):7})
JIANGXING_MAP = sanhe({(2,6,10):6,(8,0,4):0,(5,9,1):9,(11,3,7):3})
WANGSHEN_MAP = sanhe({(8,0,4):11,(2,6,10):5,(11,3,7):2,(5,9,1):8})
JIESHA_MAP = sanhe({(8,0,4):5,(2,6,10):11,(11,3,7):8,(5,9,1):2})
ZAISHA_MAP = sanhe({(8,0,4):6,(2,6,10):0,(11,3,7):9,(5,9,1):3})
LIUE_MAP = sanhe({(2,6,10):9,(8,0,4):3,(5,9,1):0,(11,3,7):6})
JINGUI_MAP = sanhe({(8,0,4):0,(11,3,7):3,(2,6,10):6,(5,9,1):9})
GUCHEN_MAP = {2:5,3:5,4:5,5:8,6:8,7:8,8:11,9:11,10:11,11:2,0:2,1:2}
GUASU_MAP = {2:1,3:1,4:1,5:4,6:4,7:4,8:7,9:7,10:7,11:10,0:10,1:10}
SIFEI_MAP = {2:{26,27},3:{26,27},4:{26,27},5:{48,59},6:{48,59},7:{48,59},
             8:{50,51},9:{50,51},10:{50,51},11:{42,53},0:{42,53},1:{42,53}}

# ---------- 特殊生成器 ----------
def generator_tianshe(pillar):
    if pillar!="day": raise ValueError
    ts={2:{14},3:{14},4:{14},5:{30},6:{30},7:{30},8:{44},9:{44},10:{44},11:{0},0:{0},1:{0}}
    def rule(cand,tp=None):
        mb=cand["month_branch"]; ds=cand["day_stem"]; db=cand["day_branch"]
        did = gz_index(ds,db) if ds is not None and db is not None else None
        if mb is not None and did is not None:
            return [cand] if mb in ts and did in ts[mb] else []
        if mb is not None:
            res=[]
            for idx in ts.get(mb,[]):
                s,b=gz_split(idx)
                if (ds is None or ds==s) and (db is None or db==b):
                    res.append({**cand,"day_stem":s,"day_branch":b})
            return res
        if did is not None:
            res=[]
            for m,idxes in ts.items():
                if did in idxes: res.append({**cand,"month_branch":m})
            return res
        res=[]
        for m,idxes in ts.items():
            for idx in idxes:
                s,b=gz_split(idx)
                if (ds is None or ds==s) and (db is None or db==b):
                    res.append({**cand,"month_branch":m,"day_stem":s,"day_branch":b})
        return res
    return rule

def generator_tiande(pillar):
    td={2:{"stem":3},3:{"branch":8},4:{"stem":8},5:{"stem":7},6:{"branch":11},7:{"stem":0},
        8:{"stem":9},9:{"branch":2},10:{"stem":2},11:{"stem":1},0:{"branch":5},1:{"stem":6}}
    def rule(cand,tp=None):
        mb=cand["month_branch"]
        if mb is None: return [cand]
        c=td[mb]
        if "stem" in c:
            s=cand.get(f"{pillar}_stem")
            if s is not None: return [cand] if s==c["stem"] else []
            else: return [{**cand,f"{pillar}_stem":c["stem"]}]
        else:
            b=cand.get(f"{pillar}_branch")
            if b is not None: return [cand] if b==c["branch"] else []
            else: return [{**cand,f"{pillar}_branch":c["branch"]}]
    return rule

def generator_tiande_he(pillar):
    td={2:{"stem":3},3:{"branch":8},4:{"stem":8},5:{"stem":7},6:{"branch":11},7:{"stem":0},
        8:{"stem":9},9:{"branch":2},10:{"stem":2},11:{"stem":1},0:{"branch":5},1:{"stem":6}}
    def rule(cand,tp=None):
        mb=cand["month_branch"]
        if mb is None: return [cand]
        c=td[mb]
        if "stem" in c:
            he=HEAVENLY_HE[c["stem"]]
            s=cand.get(f"{pillar}_stem")
            if s is not None: return [cand] if s==he else []
            else: return [{**cand,f"{pillar}_stem":he}]
        else:
            he=EARTHLY_HE[c["branch"]]
            b=cand.get(f"{pillar}_branch")
            if b is not None: return [cand] if b==he else []
            else: return [{**cand,f"{pillar}_branch":he}]
    return rule

def generator_yuede(pillar):
    yd={8:8,0:8,4:8,11:0,3:0,7:0,2:2,6:2,10:2,5:6,9:6,1:6}
    def rule(cand,tp=None):
        mb=cand["month_branch"]
        if mb is None: return [cand]
        s=cand.get(f"{pillar}_stem")
        exp=yd[mb]
        if s is not None: return [cand] if s==exp else []
        else: return [{**cand,f"{pillar}_stem":exp}]
    return rule

def generator_yuede_he(pillar):
    yd={8:8,0:8,4:8,11:0,3:0,7:0,2:2,6:2,10:2,5:6,9:6,1:6}
    def rule(cand,tp=None):
        mb=cand["month_branch"]
        if mb is None: return [cand]
        he=HEAVENLY_HE[yd[mb]]
        s=cand.get(f"{pillar}_stem")
        if s is not None: return [cand] if s==he else []
        else: return [{**cand,f"{pillar}_stem":he}]
    return rule

def generator_tianluo(pillar):
    if pillar!="day": raise ValueError
    def rule(cand,tp=None):
        ys=cand["year_stem"]; yb=cand["year_branch"]; db=cand["day_branch"]
        if ys is None or yb is None: return [cand]
        if NAYIN_WUXING[gz_index(ys,yb)]!=3: return []
        if db is not None: return [cand] if db in {10,11} else []
        return [{**cand,"day_branch":b} for b in (10,11)]
    return rule

def generator_diwang(pillar):
    if pillar!="day": raise ValueError
    def rule(cand,tp=None):
        ys=cand["year_stem"]; yb=cand["year_branch"]; db=cand["day_branch"]
        if ys is None or yb is None: return [cand]
        if NAYIN_WUXING[gz_index(ys,yb)] not in (1,4): return []
        if db is not None: return [cand] if db in {4,5} else []
        return [{**cand,"day_branch":b} for b in (4,5)]
    return rule

def generator_tianluodiwang(pillar):
    if pillar!="day": raise ValueError
    r1=generator_tianluo(pillar); r2=generator_diwang(pillar)
    return lambda cand,tp=None: r1(cand)+r2(cand)

def generator_liuxia(pillar):
    return make_rule_from_method({"source_kind":"stem","source_key":"day_stem","target_kind":"branch",
                                  "target_key_template":"{pillar}_branch","mapping":LIUXIA_MAP}, pillar)

def generator_shiling(pillar):
    if pillar not in ("day","hour"): raise ValueError
    return make_fixed_set_rule(SHILING, f"{pillar}_stem", f"{pillar}_branch")

def generator_yegui(pillar):
    if pillar!="hour": raise ValueError
    YD={29,33}; YH={9,10,11,0,1,2}
    def rule(cand,tp=None):
        ds=cand["day_stem"]; db=cand["day_branch"]; hb=cand["hour_branch"]
        did = gz_index(ds,db) if ds is not None and db is not None else None
        if did is not None:
            if did not in YD: return []
            if hb is not None: return [cand] if hb in YH else []
            else: return [{**cand,"hour_branch":b} for b in YH]
        res=[]
        for idx in YD:
            s,b=gz_split(idx)
            if (ds is None or ds==s) and (db is None or db==b):
                if hb is not None:
                    if hb in YH: res.append({**cand,"day_stem":s,"day_branch":b})
                else:
                    for hb2 in YH: res.append({**cand,"day_stem":s,"day_branch":b,"hour_branch":hb2})
        return res
    return rule

def generator_jiuchou(pillar):
    if pillar!="day": raise ValueError
    return make_fixed_set_rule(JIUCHOU, "day_stem", "day_branch")

def generator_fanyin(pillar):
    if pillar=="day": raise ValueError
    def rule(cand,tp=None):
        ds=cand["day_stem"]; db=cand["day_branch"]
        if ds is None or db is None: return [cand]
        ts=cand.get(f"{pillar}_stem"); tb=cand.get(f"{pillar}_branch")
        if ts is not None and tb is not None:
            return [cand] if (ts==ds and tb==(db+6)%12) or (tb==EARTHLY_HE[db] and stems_ke(ts,ds)) else []
        pairs=set()
        if ts is None or ts==ds:
            b1=(db+6)%12
            if tb is None or tb==b1: pairs.add((ds,b1))
        if tb is None or tb==EARTHLY_HE[db]:
            for s2 in range(10):
                if stems_ke(s2,ds) and (ts is None or ts==s2): pairs.add((s2,EARTHLY_HE[db]))
        res=[]
        for s,b in pairs:
            if (ts is None or ts==s) and (tb is None or tb==b):
                res.append({**cand,f"{pillar}_stem":s,f"{pillar}_branch":b})
        if not res and (ts is not None or tb is not None): return []
        return res if res else [cand]
    return rule

def generator_yuanchen(pillar):
    methods=[
        {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":yuanchen},
        {"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":yuanchen}
    ]
    return make_multi_method_rule(methods, pillar)

def generator_sanqi(pillar):
    def rule(cand,tp=None):
        ys=cand["year_stem"]; ms=cand["month_stem"]; ds=cand["day_stem"]; hs=cand["hour_stem"]
        if None in (ys,ms,ds,hs): return [cand]
        return [cand] if (ys,ms,ds) in [(0,4,6),(1,2,3),(8,9,7)] or (ms,ds,hs) in [(0,4,6),(1,2,3),(8,9,7)] else []
    return rule

def generator_xueren(pillar):
    return make_rule_from_method({"source_kind":"branch","source_key":"month_branch","target_kind":"branch",
                                  "target_key_template":"{pillar}_branch","mapping":XUEREN_MAP}, pillar)

def generator_guluan(pillar):
    if pillar=="day": return make_fixed_set_rule(GULUAN, "day_stem", "day_branch")
    elif pillar=="hour":
        def rule(cand,tp=None):
            ds=cand["day_stem"]; db=cand["day_branch"]; hs=cand["hour_stem"]; hb=cand["hour_branch"]
            did = gz_index(ds,db) if ds is not None and db is not None else None
            hid = gz_index(hs,hb) if hs is not None and hb is not None else None
            if did is not None and did not in GULUAN: return []
            if hid is not None and hid not in GULUAN: return []
            pdays=[i for i in GULUAN if (ds is None or ds==i%10) and (db is None or db==i%12)]
            phours=[i for i in GULUAN if (hs is None or hs==i%10) and (hb is None or hb==i%12)]
            if not pdays or not phours: return []
            res=[]
            for d in pdays:
                for h in phours:
                    res.append({**cand,"day_stem":d%10,"day_branch":d%12,"hour_stem":h%10,"hour_branch":h%12})
            return res
        return rule
    else: raise ValueError

def generator_sifei(pillar):
    if pillar!="day": raise ValueError
    def rule(cand,tp=None):
        mb=cand["month_branch"]
        if mb is None: return [cand]
        if mb not in SIFEI_MAP: return []
        allowed=SIFEI_MAP[mb]
        ds=cand["day_stem"]; db=cand["day_branch"]
        if ds is not None and db is not None: return [cand] if gz_index(ds,db) in allowed else []
        res=[]
        for idx in allowed:
            s,b=idx%10,idx%12
            if (ds is None or ds==s) and (db is None or db==b):
                res.append({**cand,"day_stem":s,"day_branch":b})
        return res
    return rule

def generator_liujiakongwang(pillar):
    def rule(cand, target_pillar=None):
        ds = cand["day_stem"]
        if ds is None:
            return [cand]
        yang_count = 0
        yin_count = 0
        for p in ["year", "month", "day", "hour"]:
            s = cand[p + "_stem"]
            b = cand[p + "_branch"]
            if s is not None and b is not None:
                if s % 2 == 0:
                    yang_count += 1
                else:
                    yin_count += 1
                if b % 2 == 0:
                    yang_count += 1
                else:
                    yin_count += 1
            else:
                return [cand]   # 有未确定的柱位，暂不约束
        if (ds % 2 == 0 and yang_count > yin_count) or (ds % 2 != 0 and yang_count < yin_count):
            return [cand]
        else:
            return []
    return rule

def generator_xunkong(pillar):
    def rule(cand,tp=None):
        ds=cand["day_stem"]; db=cand["day_branch"]
        if ds is None or db is None: return [cand]
        xun= gz_index(ds,db)//10*10
        kong={(xun%12+10)%12,(xun%12+11)%12}
        tb=cand.get(f"{pillar}_branch")
        if tb is not None: return [cand] if tb in kong else []
        else: return [{**cand,f"{pillar}_branch":b} for b in kong]
    return rule

def generator_feiren(pillar):
    m={s:(YANGREN_MAP[s]+6)%12 for s in range(10)}
    return make_rule_from_method({"source_kind":"stem","source_key":"day_stem","target_kind":"branch",
                                  "target_key_template":"{pillar}_branch","mapping":m}, pillar)

def generator_tianyi_yue(pillar):
    return make_rule_from_method({"source_kind":"branch","source_key":"month_branch","target_kind":"branch",
                                  "target_key_template":"{pillar}_branch","mapping":lambda b:(b-1)%12}, pillar)

def generator_tongzi(pillar):
    sm={2:{2,0},3:{2,0},4:{2,0},5:{3,7},6:{3,7},7:{3,7},8:{5,8},9:{5,8},10:{5,8},11:{6,9},0:{6,9},1:{6,9}}
    nbm={0:{6,3},2:{6,3},1:{9,10},3:{9,10},4:{4,5}}
    nsm={0:{0,1},2:{2,3},1:{4,5},3:{6,7},4:{8,9}}
    def r1(cand):
        if pillar!="hour": return []
        mb=cand["month_branch"]
        if mb is None: return [cand]
        v=sm.get(mb,set())
        if not v: return []
        hb=cand["hour_branch"]
        if hb is not None: return [cand] if hb in v else []
        else: return [{**cand,"hour_branch":b} for b in v]
    def r2(cand):
        if pillar not in ("day","hour"): return []
        ys=cand["year_stem"]; yb=cand["year_branch"]
        if ys is None or yb is None: return [cand]
        wx=NAYIN_WUXING[gz_index(ys,yb)]
        v=nbm.get(wx,set())
        if not v: return []
        tb=cand.get(f"{pillar}_branch")
        if tb is not None: return [cand] if tb in v else []
        else: return [{**cand,f"{pillar}_branch":b} for b in v]
    def r3(cand):
        if pillar not in ("day","hour"): return []
        ys=cand["year_stem"]; yb=cand["year_branch"]
        if ys is None or yb is None: return [cand]
        wx=NAYIN_WUXING[gz_index(ys,yb)]
        v=nsm.get(wx,set())
        if not v: return []
        ts=cand.get(f"{pillar}_stem")
        if ts is not None: return [cand] if ts in v else []
        else: return [{**cand,f"{pillar}_stem":s} for s in v]
    return lambda cand,tp=None: r1(cand)+r2(cand)+r3(cand)

def generator_dexiu(pillar):
    def get_set(mb):
        if mb in (2,6,10): return {2,3,4,9}
        if mb in (8,0,4): return {8,9,4,5,2,7,0,5}
        if mb in (5,9,1): return {6,7,1,6}
        if mb in (11,3,7): return {0,1,3,8}
        return set()
    def rule(cand,tp=None):
        mb=cand["month_branch"]
        if mb is None: return [cand]
        v=get_set(mb)
        ts=cand.get(f"{pillar}_stem")
        if ts is not None: return [cand] if ts in v else []
        else: return [{**cand,f"{pillar}_stem":s} for s in v]
    return rule

def generator_jinshen(pillar):
    if pillar not in ("day","hour"): return lambda cand,tp=None: []
    rf=make_fixed_set_rule(JINSHEN, f"{pillar}_stem", f"{pillar}_branch")
    if pillar=="hour":
        def rc(cand,tp=None):
            ds=cand["day_stem"]; hb=cand["hour_branch"]
            if ds is not None and hb is not None:
                return [cand] if (ds==1 and hb==1) or (ds==5 and hb==5) or (ds==9 and hb==9) else []
            res=[]
            if ds is not None:
                for b in ([1] if ds==1 else [5] if ds==5 else [9] if ds==9 else []):
                    if hb is None or hb==b: res.append({**cand,"hour_branch":b})
                return res
            elif hb is not None:
                for d in ([1] if hb==1 else [5] if hb==5 else [9] if hb==9 else []):
                    if ds is None or ds==d: res.append({**cand,"day_stem":d})
                return res
            else:
                for d,b in [(1,1),(5,5),(9,9)]: res.append({**cand,"day_stem":d,"hour_branch":b})
                return res
        return lambda cand,tp=None: rf(cand)+rc(cand)
    return rf

def generator_rigui(pillar):
    if pillar!="hour": raise ValueError
    RD={23,39}; RH={3,4,5,6,7,8}
    def rule(cand,tp=None):
        ds=cand["day_stem"]; db=cand["day_branch"]; hs=cand["hour_stem"]; hb=cand["hour_branch"]
        did=gz_index(ds,db) if ds is not None and db is not None else None
        if did is not None:
            if did not in RD: return []
            if hb is not None: return [cand] if hb in RH else []
            else: return [{**cand,"hour_branch":b} for b in RH]
        if hb is not None:
            if hb not in RH: return []
            res=[]
            for idx in RD:
                s,b=gz_split(idx)
                if (ds is None or ds==s) and (db is None or db==b):
                    res.append({**cand,"day_stem":s,"day_branch":b})
            return res
        res=[]
        for idx in RD:
            s,b=gz_split(idx)
            if (ds is None or ds==s) and (db is None or db==b):
                for hb2 in RH:
                    nc={**cand,"day_stem":s,"day_branch":b,"hour_branch":hb2}
                    if hs is not None: nc["hour_stem"]=hs
                    res.append(nc)
        return res
    return rule

# ---------- 生成器注册 ----------
def make_generator(data):
    if isinstance(data, list):
        def gen(pillar, option=None):
            methods = data if option is None else [m for m in data if m.get("label")==option]
            if not methods: raise ValueError(f"无此起法: {option}")
            return make_multi_method_rule(methods, pillar)
        return gen
    else:
        return lambda pillar, option=None: data(pillar)

SHENSHA_LIST = [
    ("魁罡", lambda p: make_fixed_set_rule(KUIGANG, "day_stem", "day_branch")),
    ("六秀", lambda p: make_fixed_set_rule(LIUXIU, "day_stem", "day_branch")),
    ("阴差阳错", lambda p: make_fixed_set_rule(YINCHAYANGCUO, "day_stem", "day_branch")),
    ("十恶大败", lambda p: make_fixed_set_rule(SHIEDABAI, "day_stem", "day_branch")),
    ("八专", lambda p: make_fixed_set_rule(BAZHUAN, "day_stem", "day_branch")),
    ("金神", generator_jinshen),
    ("禄神", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":LU_MAP}]),
    ("金舆", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JINYU_MAP},
              {"label":"年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JINYU_MAP}]),
    ("阳刃", [{"label":"口诀1","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YANGREN_MAP},
              {"label":"口诀2","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YANGREN_V2},
              {"label":"口诀3","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YANGREN_V3}]),
    ("披头", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":PITOU_MAP}]),
    ("披麻", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":PIMA_MAP}]),
    ("红鸾", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HONGLUAN_MAP}]),
    ("天喜", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANXI_MAP}]),
    ("丧门", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":sangmen}]),
    ("吊客", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":diaoke}]),
    ("病符", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":bingfu}]),
    ("钩绞", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":goujiao}]),
    ("桃花", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAOHUA_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAOHUA_MAP}]),
    ("驿马", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YIMA_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YIMA_MAP}]),
    ("华盖", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HUAGAI_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HUAGAI_MAP}]),
    ("将星", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIANGXING_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIANGXING_MAP}]),
    ("亡神", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WANGSHEN_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WANGSHEN_MAP}]),
    ("劫煞", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIESHA_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIESHA_MAP}]),
    ("灾煞", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":ZAISHA_MAP}]),
    ("六厄", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":LIUE_MAP}]),
    ("金匮", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JINGUI_MAP}]),
    ("文昌", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WENCHANG_MAP},
              {"label":"年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WENCHANG_MAP}]),
    ("福星贵人", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":FUXING_MAP},
                  {"label":"年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":FUXING_MAP}]),
    ("太极贵人", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAIJI_MAP},
                  {"label":"年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAIJI_MAP}]),
    ("国印贵人", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUOYIN_MAP},
                  {"label":"年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUOYIN_MAP}]),
    ("天乙贵人", [{"label":"口诀1日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANYI_MAP},
                  {"label":"口诀1年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANYI_MAP},
                  {"label":"口诀3日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANYI_V3},
                  {"label":"口诀3年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANYI_V3}]),
    ("红艳", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HONGYAN_MAP},
              {"label":"年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HONGYAN_MAP}]),
    ("词馆", [
        {"label":"日干->柱","source_kind":"stem","source_key":"day_stem","target_kind":"pillar","target_key_template":"{pillar}","mapping":CIGUAN_MAP},
        {"label":"年干->柱","source_kind":"stem","source_key":"year_stem","target_kind":"pillar","target_key_template":"{pillar}","mapping":CIGUAN_MAP},
        {"label":"纳音支","source_kind":"nayin_wuxing","source_key":"year","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":{2:2,3:5,4:11,0:8,1:11}},
        {"label":"纳音临官","source_kind":"nayin_wuxing","source_key":"year","target_kind":"pillar","target_key_template":"{pillar}","mapping":{2:26,3:41,0:8}}
    ]),
    ("学堂", [
        {"label":"学堂纳音","source_kind":"nayin_wuxing","source_key":"year","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":{2:11,3:2,4:8,0:5,1:8}},
        {"label":"学堂日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":XUETANG_STEM},
        {"label":"学堂同临官","source_kind":"nayin_wuxing","source_key":"year","target_kind":"pillar","target_key_template":"{pillar}","mapping":{4:23,1:59}}
    ]),
    ("孤辰", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUCHEN_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUCHEN_MAP}]),
    ("寡宿", [{"label":"年支","source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUASU_MAP},
              {"label":"日支","source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUASU_MAP}]),
    ("天赦", generator_tianshe),
    ("天德", generator_tiande),
    ("天德合", generator_tiande_he),
    ("月德", generator_yuede),
    ("月德合", generator_yuede_he),
    ("天罗", generator_tianluo),
    ("地网", generator_diwang),
    ("天罗地网", generator_tianluodiwang),
    ("流霞", generator_liuxia),
    ("天厨", [{"label":"日干","source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANCHU_MAP},
              {"label":"年干","source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANCHU_MAP}]),
    ("十灵", generator_shiling),
    ("夜贵", generator_yegui),
    ("日贵", generator_rigui),
    ("九丑", generator_jiuchou),
    ("反吟", generator_fanyin),
    ("元辰", generator_yuanchen),
    ("三奇贵人", generator_sanqi),
    ("血刃", generator_xueren),
    ("孤鸾", generator_guluan),
    ("四废", generator_sifei),
    ("六甲空亡", generator_liujiakongwang),
    ("空亡", generator_xunkong),
    ("飞刃", generator_feiren),
    ("天医", generator_tianyi_yue),
    ("童子", generator_tongzi),
    ("德秀贵人", generator_dexiu),
    ("暗金", lambda p: (lambda cand,tp=None: []) if p!="hour" else make_rule_from_method(
        {"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":ANJIN_MAP}, p)),
]

SHENSHA_ALIASES = {
    "天乙":"天乙贵人","天德贵人":"天德","天德贵":"天德","月德贵人":"月德","月德贵":"月德",
    "魁罡日":"魁罡","六秀日":"六秀","阴差阳错日":"阴差阳错","十恶大败日":"十恶大败",
    "八专日":"八专","九丑日":"九丑","孤鸾日":"孤鸾","四废日":"四废",
    "十灵日":"十灵","十灵时":"十灵","金神日":"金神","金神时":"金神",
    "禄神贵人":"禄神","金舆贵人":"金舆","羊刃":"阳刃","飞刃煞":"飞刃",
    "文昌贵人":"文昌","福星":"福星贵人","太极":"太极贵人","国印":"国印贵人",
    "天厨贵人":"天厨","词馆贵人":"词馆","学堂贵":"学堂","学堂":"学堂",
    "天赦日":"天赦","天德合贵人":"天德合","月德合贵人":"月德合",
    "天罗地网":"天罗地网","反吟煞":"反吟","大耗":"元辰","旬空":"空亡",
    "咸池":"桃花","驿马星":"驿马","华盖贵人":"华盖","将星贵人":"将星",
    "劫煞贵人":"劫煞","白虎煞":"灾煞","亡神煞":"亡神","金匮星":"金匮",
    "血刃煞":"血刃","童子煞":"童子","夜贵贵人":"夜贵","日贵贵人":"日贵",
    "孤辰煞":"孤辰","寡宿煞":"寡宿","三奇":"三奇贵人","六甲空亡煞":"六甲空亡",
    "流霞煞":"流霞","红艳煞":"红艳","天医贵人":"天医","披头煞":"披头",
    "披麻煞":"披麻","丧门煞":"丧门","吊客煞":"吊客","病符煞":"病符",
    "钩绞煞":"钩绞","红鸾星":"红鸾","天喜星":"天喜","德秀":"德秀贵人",
    "暗金煞":"暗金",
}

def resolve_alias(n): return SHENSHA_ALIASES.get(n,n)
RULE_GENERATORS = {name:make_generator(data) for name,data in SHENSHA_LIST}

def parse_condition(cond_str):
    pillar_map = {"年柱":"year","月柱":"month","日柱":"day","时柱":"hour", "全局":"day"}
    m = re.match(r"^(年柱|月柱|日柱|时柱)(.+)$", cond_str.strip())
    if not m: raise ValueError("格式错误")
    pillar = pillar_map[m.group(1)]; rest = m.group(2).strip()
    opt = re.match(r"(.+?)\((.+)\)$", rest)
    if opt: shensha = opt.group(1).strip(); option = opt.group(2).strip()
    else: shensha = rest; option = None
    shensha = resolve_alias(shensha)
    if shensha not in RULE_GENERATORS: raise ValueError(f"未知神煞: {shensha}")
    return pillar, shensha, option

# ---------- 求解器 ----------
class ConstraintSolver:
    def __init__(self):
        self.rules = []
        self.builtin = [self._validate_pillars, self._validate_month, self._validate_hour]
        self.user_conditions = set()

    def add_rule(self, rule_func, pillar, shensha):
        self.rules.append((rule_func, pillar, shensha))
        self.user_conditions.add((pillar, shensha))

    def _validate_pillars(self,cand):
        for p in ["year","month","day","hour"]:
            s=cand[p+"_stem"]; b=cand[p+"_branch"]
            if s is not None and b is not None and s%2!=b%2: return []
        return [cand]

    def _validate_month(self,cand):
        ys=cand["year_stem"]; mb=cand["month_branch"]; ms=cand["month_stem"]
        if ys is not None and mb is not None:
            c=month_stem(ys,mb)
            if ms is None: return [{**cand,"month_stem":c}]
            elif ms!=c: return []
        elif ys is not None and ms is not None and mb is None:
            return [{**cand,"month_branch":b} for b in range(12) if month_stem(ys,b)==ms]
        elif ms is not None and mb is not None and ys is None:
            off=(mb-2)%12; base=(ms-off)%10
            return [{**cand,"year_stem":y} for y in range(10) if MONTH_STEM_BASE[y]==base]
        return [cand]

    def _validate_hour(self,cand):
        ds=cand["day_stem"]; hb=cand["hour_branch"]; hs=cand["hour_stem"]
        if ds is not None and hb is not None:
            c=hour_stem(ds,hb)
            if hs is None: return [{**cand,"hour_stem":c}]
            elif hs!=c: return []
        elif ds is not None and hs is not None and hb is None:
            return [{**cand,"hour_branch":b} for b in range(12) if hour_stem(ds,b)==hs]
        elif hs is not None and hb is not None and ds is None:
            base=(hs-hb)%10
            return [{**cand,"day_stem":d} for d in range(10) if HOUR_STEM_BASE[d]==base]
        return [cand]

    def _rule_priority(self, r):
        _,pillar,shen = r
        cat = {"魁罡":"日柱固定","六秀":"日柱固定","阴差阳错":"日柱固定","十恶大败":"日柱固定",
               "八专":"日柱固定","九丑":"日柱固定","孤鸾":"日柱固定","十灵":"日柱固定","金神":"日柱固定",
               "德秀贵人":"月柱锁定","天德":"月柱锁定","月德":"月柱锁定","夜贵":"日时复合","日贵":"日时复合"}.get(shen,"普通")
        if cat=="日柱固定" and pillar=="day": return 0
        if cat=="月柱锁定" and pillar=="month": return 1
        if cat=="日时复合" and pillar=="hour": return 2
        return 3

    def solve(self, max_iter=20, max_completion=10000, strict=False):
        ordered = sorted(self.rules, key=self._rule_priority)
        rule_funcs = [r[0] for r in ordered]
        candidates = [empty_candidate()]
        MAX_CAND = 500000; INTER = 5000000

        for _ in range(max_iter):
            new_cand = []
            for cand in candidates:
                temp = [cand]; fail = False
                for rule in rule_funcs + self.builtin:
                    nxt = []
                    for c in temp:
                        nxt.extend(rule(c))
                        if len(nxt) > INTER: fail=True; break
                    if fail: break
                    temp = nxt
                    if not temp: break
                if fail: continue
                new_cand.extend(temp)
            new_cand = deduplicate(new_cand)
            if len(new_cand) > MAX_CAND: new_cand = new_cand[:MAX_CAND]
            if set(candidate_tuple(c) for c in candidates) == set(candidate_tuple(c) for c in new_cand): break
            candidates = new_cand
            if not candidates: break

        before_strict = candidates[:]
        if strict:
            candidates = self._strict_filter(candidates)
            if not candidates: candidates = before_strict

        before_comp = candidates[:]
        if 0 < len(candidates) <= 500:
            completed = []
            for c in candidates:
                if len(completed) >= max_completion: break
                for comp in self._complete_candidate(c):
                    if len(completed) >= max_completion: break
                    temp = [comp]
                    for r in [self._validate_month, self._validate_hour]:
                        nxt=[]
                        for cc in temp: nxt.extend(r(cc))
                        temp=nxt
                        if not temp: break
                    completed.extend(temp)
            if 0 < len(completed) <= max_completion:
                candidates = deduplicate(completed)
            else:
                candidates = before_comp
        return candidates

    def _complete_candidate(self, cand):
        res=[cand]
        # 补全月柱
        new=[]
        for c in res:
            ys=c["year_stem"]; mb=c["month_branch"]; ms=c["month_stem"]
            if ys is not None:
                if mb is None and ms is None:
                    for b in range(12): new.append({**c,"month_branch":b,"month_stem":month_stem(ys,b)})
                elif mb is None and ms is not None:
                    for b in range(12):
                        if month_stem(ys,b)==ms: new.append({**c,"month_branch":b})
                elif mb is not None and ms is None:
                    new.append({**c,"month_stem":month_stem(ys,mb)})
                else: new.append(c)
            else: new.append(c)
        res=new; new=[]
        for c in res:
            ds=c["day_stem"]; hb=c["hour_branch"]; hs=c["hour_stem"]
            if ds is not None:
                if hb is None and hs is None:
                    for b in range(12): new.append({**c,"hour_branch":b,"hour_stem":hour_stem(ds,b)})
                elif hb is None and hs is not None:
                    for b in range(12):
                        if hour_stem(ds,b)==hs: new.append({**c,"hour_branch":b})
                elif hb is not None and hs is None:
                    new.append({**c,"hour_stem":hour_stem(ds,hb)})
                else: new.append(c)
            else: new.append(c)
        res=new; new=[]
        for p in ["year","day"]:
            for c in res:
                s=c[p+"_stem"]; b=c[p+"_branch"]
                if s is None and b is None:
                    for i in range(10):
                        for j in range(12):
                            if i%2==j%2: new.append({**c,p+"_stem":i,p+"_branch":j})
                elif s is not None and b is None:
                    for j in range(12):
                        if s%2==j%2: new.append({**c,p+"_branch":j})
                elif s is None and b is not None:
                    for i in range(10):
                        if i%2==b%2: new.append({**c,p+"_stem":i})
                else: new.append(c)
            res=new; new=[]
        return res

    def _strict_filter(self, cands):
        final=[]
        for c in cands:
            for full in self._complete_candidate(c):
                if not self._has_extra(full): final.append(full)
        return deduplicate(final)

    def _has_extra(self, full):
        specified = {shen for _,shen in self.user_conditions}
        RESTRICT = {"天赦":["day"],"天罗":["day"],"地网":["day"],"天罗地网":["day"],"十灵":["day","hour"],
                    "夜贵":["hour"],"日贵":["hour"],"九丑":["day"],"反吟":["year","month","hour"],
                    "孤鸾":["day","hour"],"四废":["day"],"暗金":["hour"],"金神":["day","hour"],
                    "魁罡":["day"],"六秀":["day"],"阴差阳错":["day"],"十恶大败":["day"],"八专":["day"],
                    "三奇贵人":["day"]}
        for shen,gen in RULE_GENERATORS.items():
            if shen in specified: continue
            for pillar in RESTRICT.get(shen, ["year","month","day","hour"]):
                try:
                    if gen(pillar)(full): return True
                except: pass
        return False

# ---------- 入口 ----------
def format_candidate(c):
    def fmt(s, b):
        if s is None or b is None:
            return "??"
        return STEMS[s] + BRANCHES[b]
    return (f"{fmt(c['year_stem'],c['year_branch'])} "
            f"{fmt(c['month_stem'],c['month_branch'])} "
            f"{fmt(c['day_stem'],c['day_branch'])} "
            f"{fmt(c['hour_stem'],c['hour_branch'])}")
if __name__ == "__main__":
    solver = ConstraintSolver()
    print("八字逆向推理引擎 v6.2")
    while True:
        cmd = input(">> ").strip()
        if cmd=="exit": break
        if cmd.startswith("run"):
            strict = cmd.endswith(" --strict")
            for c in solver.solve(strict=strict): print(format_candidate(c))
        else:
            cond = cmd[:-9] if cmd.endswith(" --strict") else cmd
            try:
                p,s,o = parse_condition(cond)
                rule = RULE_GENERATORS[s](p,o)
                solver.add_rule(rule,p,s)
            except Exception as e: print(f"错误：{e}")