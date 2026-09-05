# -*- coding: utf-8 -*-
"""
50 周恐慌指数计算
- 加载 jsonl 历史帖子
- 过滤资讯/公告/自媒体
- 词典法情感分析（纯规则，快，避免 SnowNLP 对 23 万条的耗时）
- 按 ISO 周聚合，计算每周恐慌指数
"""
import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nlp.sentiment import sentiment_score, clean_text

BASE = os.path.dirname(os.path.abspath(__file__))
_HIST = sys.argv[1] if len(sys.argv) > 1 else "eastmoney_history.jsonl"
HIST_FILE = os.path.join(BASE, "data", _HIST)
OUT_NAME = sys.argv[2] if len(sys.argv) > 2 else "weekly_panic.json"

MEDIA_SUFFIX = ("资讯", "报道", "观察", "财经社", "财讯社", "新闻", "直播", "前沿", "公社", "翻译官")


def is_media(p: dict) -> bool:
    author = p.get("author", "")
    text = (p.get("title", "") + " " + p.get("content", ""))
    if any(s in author for s in MEDIA_SUFFIX):
        return True
    if any(k in text for k in ("邀您观看", "邀您", "锁定", "请点击标题", "完整早报")):
        return True
    return False


def iso_week(dt: datetime):
    """返回 ISO 周起始日（周一）"""
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


def load_and_analyze(hist_file: str = None):
    """加载历史帖子并做词典法情感分析，返回 posts_by_week"""
    fp = hist_file or HIST_FILE
    weeks = defaultdict(list)
    total = 0
    skipped = 0
    with open(fp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
            except Exception:
                continue
            total += 1
            # 过滤资讯/公告/自媒体
            if p.get("post_type") in (1, 3):
                skipped += 1
                continue
            if p.get("post_type") == 20 and is_media(p):
                skipped += 1
                continue
            # 词典法情感
            text = clean_text(p.get("title", "") + " " + p.get("content", ""))
            r = sentiment_score(text)
            pt = p.get("publish_time", "")
            try:
                dt = datetime.strptime(pt[:10], "%Y-%m-%d")
            except Exception:
                continue
            wk = iso_week(dt)
            weeks[wk].append({
                "label": r["label"],
                "strength": r["strength"],
                "read": p.get("read", 0) or 0,
                "reply": p.get("reply", 0) or 0,
            })
    print(f"加载 {total} 条, 过滤 {skipped} 条资讯/公告/自媒体, 有效 {total - skipped} 条")
    return weeks


def week_stats(week_posts: list) -> dict:
    n = len(week_posts)
    bull = sum(1 for p in week_posts if p["label"] == "看多")
    bear = sum(1 for p in week_posts if p["label"] == "看空")
    neutral = sum(1 for p in week_posts if p["label"] == "中性")
    bear_ratio = bear / (bull + bear) if (bull + bear) > 0 else 0.5
    # 热度加权情感
    tw = 0.0
    ws = 0.0
    for p in week_posts:
        w = 1.0 + (p["read"] + p["reply"] * 2) ** 0.5
        tw += w
        ws += p["strength"] * w
    mean_strength = ws / tw if tw > 0 else 0.0
    sentiment = (1.0 - mean_strength) / 2.0
    return {
        "total": n, "bull": bull, "bear": bear, "neutral": neutral,
        "bear_ratio": round(bear_ratio, 4), "mean_strength": round(mean_strength, 4),
        "sentiment": round(sentiment, 4),
    }


def compute_weekly_panic(weeks: dict) -> list:
    """计算每周恐慌指数
    公式：Panic = 看空帖数 × (0.2 - 情感均值) / 0.2
    情感均值 = mean_strength（热度加权单帖得分，-1~+1）
    分档：>3000 极度恐慌；其余按 panic 分位数（相对程度）
    """
    sorted_weeks = sorted(weeks.keys())
    # 先算原始 panic
    raw = []
    for wk in sorted_weeks:
        st = week_stats(weeks[wk])
        panic = st["bear"] * (0.2 - st["mean_strength"]) / 0.2
        raw.append((wk, st, panic))

    # 分位数阈值（20/50/80 分位）
    ps = sorted(p for _, _, p in raw)
    n = len(ps)
    q80 = ps[min(int(n * 0.8), n - 1)]
    q50 = ps[min(int(n * 0.5), n - 1)]
    q20 = ps[min(int(n * 0.2), n - 1)]

    result = []
    for wk, st, panic in raw:
        if panic > 3000:
            level = "极度恐慌"
        elif panic >= q80:
            level = "高恐慌"
        elif panic >= q50:
            level = "恐慌"
        elif panic >= q20:
            level = "中性偏谨慎"
        else:
            level = "温和"

        result.append({
            "week_start": wk,
            "panic": round(panic, 1),
            "level": level,
            "total": st["total"],
            "bull": st["bull"],
            "bear": st["bear"],
            "neutral": st["neutral"],
            "bear_ratio": st["bear_ratio"],
            "mean_strength": st["mean_strength"],
        })
    return result


def main():
    weeks = load_and_analyze()
    print(f"共 {len(weeks)} 周")
    weekly = compute_weekly_panic(weeks)

    out = os.path.join(BASE, "data", OUT_NAME)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(weekly, f, ensure_ascii=False, indent=2)
    print(f"周频恐慌指数已保存: {out}")
    # 打印概览
    print("\n=== 最近 10 周 ===")
    for w in weekly[-10:]:
        print(f"  {w['week_start']} | 恐慌{w['panic']:>5} {w['level']} | 帖{w['total']:>4} 多{w['bull']:>3} 空{w['bear']:>3} | 看空比{w['bear_ratio']*100:.0f}%")


if __name__ == "__main__":
    main()
