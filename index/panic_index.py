# -*- coding: utf-8 -*-
"""
恐慌指数计算模型
数据源：东方财富股吧 + 雪球（小米集团-W / 01810.HK）

公式（0-100，越高越恐慌）：
    Panic = 100 × ( w1·看空比 + w2·情感指数 + w3·发帖量指数 )

    1) 看空比 bear_ratio = N看空 / (N看空 + N看多)          —— 方向明确的帖子中，看空占比
    2) 情感指数 sentiment  = (1 - mean(strength)) / 2        —— strength∈[-1,1]，全看空=1，全看多=0
       其中 strength 按"阅读量+评论量"加权，让高热度帖子影响力更大
    3) 发帖量指数 volume   = clamp(posts / baseline, 0, 3) / 3 —— 发帖量相对基线放大，恐慌时帖子激增

权重：w1=0.40, w2=0.35, w3=0.25（可配置）
"""
import json
import math
from collections import defaultdict
from datetime import datetime

WEIGHTS = {"bear_ratio": 0.45, "sentiment": 0.40, "volume": 0.15}


def compute_stats(posts: list) -> dict:
    """对带情感标签的帖子列表做统计"""
    bull = [p for p in posts if p["label"] == "看多"]
    bear = [p for p in posts if p["label"] == "看空"]
    neutral = [p for p in posts if p["label"] == "中性"]

    n = len(posts)
    n_bull, n_bear, n_neutral = len(bull), len(bear), len(neutral)

    # 看空/看多比（只看有方向帖子）
    if n_bull + n_bear > 0:
        bear_ratio = n_bear / (n_bull + n_bear)
    else:
        bear_ratio = 0.5

    # 情感指数：按热度(阅读+评论)加权的 strength 均值
    total_w = 0.0
    weighted_sum = 0.0
    for p in posts:
        heat = 1.0 + math.log1p(p.get("read", 0) + p.get("reply", 0) * 2)
        w = heat
        weighted_sum += p["strength"] * w
        total_w += w
    mean_strength = weighted_sum / total_w if total_w > 0 else 0.0
    sentiment = (1.0 - mean_strength) / 2.0  # 映射到 [0,1]

    return {
        "total": n,
        "bull": n_bull,
        "bear": n_bear,
        "neutral": n_neutral,
        "bear_ratio": round(bear_ratio, 4),
        "bull_bear_ratio": round(n_bull / n_bear, 4) if n_bear > 0 else None,
        "mean_strength": round(mean_strength, 4),
        "sentiment": round(sentiment, 4),
        "avg_snownlp": round(sum(p["snownlp"] for p in posts) / n, 4) if n else 0,
    }


def compute_panic(posts: list, baseline_posts: int = None) -> dict:
    """计算恐慌指数"""
    stats = compute_stats(posts)
    n = stats["total"]

    # 发帖量指数：今日发帖量 / 前3个完整天的日均发帖量（放量倍数，2倍封顶）
    if baseline_posts is None:
        daily = group_by_day(posts)
        if len(daily) >= 4:
            # 取最近 3 个完整天（不含今天，今天=最后一天）的日均作为基线
            recent = [d["total"] for d in daily[-4:-1]]
            prev_avg = sum(recent) / len(recent)
            baseline_posts = max(prev_avg, 1)
            today_cnt = daily[-1]["total"]
        elif len(daily) >= 2:
            today_cnt = daily[-1]["total"]
            prev_avg = sum(d["total"] for d in daily[:-1]) / len(daily[:-1])
            baseline_posts = max(prev_avg, 1)
        else:
            today_cnt = n
            baseline_posts = max(n, 1)
    else:
        today_cnt = n

    volume_factor = min(today_cnt / baseline_posts, 2.0) / 2.0  # 2倍封顶映射到1

    bear_ratio = stats["bear_ratio"]
    sentiment = stats["sentiment"]

    panic = 100.0 * (
        WEIGHTS["bear_ratio"] * bear_ratio
        + WEIGHTS["sentiment"] * sentiment
        + WEIGHTS["volume"] * volume_factor
    )

    # 定性分档
    if panic >= 70:
        level = "极度恐慌"
    elif panic >= 55:
        level = "恐慌"
    elif panic >= 45:
        level = "中性偏谨慎"
    elif panic >= 30:
        level = "中性偏乐观"
    elif panic >= 15:
        level = "乐观"
    else:
        level = "极度乐观"

    return {
        "panic_index": round(panic, 1),
        "level": level,
        "baseline_posts": round(baseline_posts, 1),
        "today_posts": today_cnt,
        "volume_factor": round(volume_factor, 4),
        **stats,
    }


def group_by_day(posts: list, now_year: int = None) -> list:
    """按天聚合（update 字段），返回每日统计时序"""
    days = defaultdict(list)
    for p in posts:
        upd = p.get("update", "")
        key = re_match_date(upd)
        if key:
            days[key].append(p)
    series = []
    for key in sorted(days.keys()):
        st = compute_stats(days[key])
        series.append({"date": key, "total": st["total"], "bull": st["bull"],
                       "bear": st["bear"], "neutral": st["neutral"],
                       "bear_ratio": st["bear_ratio"], "sentiment": st["sentiment"],
                       "mean_strength": st["mean_strength"]})
    return series


def re_match_date(upd: str):
    import re
    # 支持两种格式："2026-08-17 13:50:09" 和 "08-17 04:03"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", upd)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{2})-(\d{2})", upd)
    if m:
        return f"{datetime.now().year}-{m.group(1)}-{m.group(2)}"
    return None


def load_and_compute(eastmoney_json: str, xueqiu_json: str = None,
                     baseline_posts: int = None) -> dict:
    """加载东财(+雪球)数据并计算恐慌指数"""
    with open(eastmoney_json, encoding="utf-8") as f:
        em_posts = json.load(f)

    all_posts = []
    for p in em_posts:
        all_posts.append({
            "postid": p["postid"],
            "title": p["title"],
            "label": p.get("label", "中性"),
            "strength": p.get("strength", 0.0),
            "read": p.get("read", 0),
            "reply": p.get("reply", 0),
            "snownlp": p.get("snownlp", 0.5),
            "update": p.get("update", ""),
            "author": p.get("author", ""),
            "source": "eastmoney",
        })
    if xueqiu_json:
        with open(xueqiu_json, encoding="utf-8") as f:
            xq = json.load(f)
        for p in xq:
            all_posts.append({
                "postid": p.get("postid", ""),
                "title": p.get("title", ""),
                "label": p.get("label", "中性"),
                "strength": p.get("strength", 0.0),
                "read": p.get("read", 0),
                "reply": p.get("reply", 0),
                "snownlp": p.get("snownlp", 0.5),
                "update": p.get("update", ""),
                "author": p.get("author", ""),
                "source": "xueqiu",
            })

    panic = compute_panic(all_posts, baseline_posts)
    daily = group_by_day(all_posts)
    return {"panic": panic, "daily": daily, "posts": all_posts}
