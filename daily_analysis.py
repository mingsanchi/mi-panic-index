# -*- coding: utf-8 -*-
"""
日频恐慌指数计算（通用）
- 加载 jsonl 历史帖子
- 过滤资讯/公告/自媒体
- 词典法情感分析
- 按日聚合，计算每日恐慌指数
用法: python daily_analysis.py <hist_jsonl> <start_date> <end_date> <out_json>
示例: python daily_analysis.py eastmoney_history.jsonl 2026-06-04 2026-09-02 mi_90days.json
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nlp.sentiment import sentiment_score, clean_text

BASE = os.path.dirname(os.path.abspath(__file__))
HIST = sys.argv[1] if len(sys.argv) > 1 else "eastmoney_history.jsonl"
START = sys.argv[2] if len(sys.argv) > 2 else "2026-06-04"
END = sys.argv[3] if len(sys.argv) > 3 else "2026-09-02"
OUT = sys.argv[4] if len(sys.argv) > 4 else "mi_90days.json"

HIST_FILE = os.path.join(BASE, "data", HIST)
OUT_FILE = os.path.join(BASE, "data", OUT)

MEDIA_SUFFIX = ("资讯", "报道", "观察", "财经社", "财讯社", "新闻", "直播", "前沿", "公社", "翻译官")


def is_media(p: dict) -> bool:
    author = p.get("author", "")
    text = (p.get("title", "") + " " + p.get("content", ""))
    if any(s in author for s in MEDIA_SUFFIX):
        return True
    if any(k in text for k in ("邀您观看", "邀您", "锁定", "请点击标题", "完整早报")):
        return True
    return False


def main():
    days = defaultdict(list)
    total = 0
    skipped = 0
    in_window = 0
    with open(HIST_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
            except Exception:
                continue
            total += 1
            pt = p.get("publish_time", "")[:10]
            if not (START <= pt <= END):
                continue
            in_window += 1
            # 过滤资讯/公告/自媒体
            if p.get("post_type") in (1, 3):
                skipped += 1
                continue
            if p.get("post_type") == 20 and is_media(p):
                skipped += 1
                continue
            text = clean_text(p.get("title", "") + " " + p.get("content", ""))
            r = sentiment_score(text)
            days[pt].append({
                "label": r["label"],
                "strength": r["strength"],
                "read": p.get("read", 0) or 0,
                "reply": p.get("reply", 0) or 0,
            })
    print(f"jsonl 总 {total} 条，窗口内 {in_window} 条，过滤 {skipped} 条资讯/公告/自媒体")

    result = []
    for d in sorted(days):
        posts = days[d]
        n = len(posts)
        bull = sum(1 for x in posts if x["label"] == "看多")
        bear = sum(1 for x in posts if x["label"] == "看空")
        neutral = sum(1 for x in posts if x["label"] == "中性")
        bear_ratio = bear / (bull + bear) if (bull + bear) > 0 else 0.5
        tw = ws = 0.0
        for x in posts:
            w = 1.0 + (x["read"] + x["reply"] * 2) ** 0.5
            tw += w
            ws += x["strength"] * w
        mean_strength = ws / tw if tw > 0 else 0.0
        panic = bear * (0.2 - mean_strength) / 0.2
        result.append({
            "date": d,
            "total": n,
            "bull": bull,
            "bear": bear,
            "neutral": neutral,
            "bear_ratio": round(bear_ratio, 4),
            "mean_strength": round(mean_strength, 4),
            "panic": round(panic, 1),
        })

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"共 {len(result)} 天，已保存 {OUT_FILE}")
    print("\n=== 最近 8 天 ===")
    for r in result[-8:]:
        print(f"  {r['date']} | panic {r['panic']:>6} | 帖{r['total']:>4} 多{r['bull']:>3} 空{r['bear']:>3} | 看空比 {r['bear_ratio']*100:.0f}%")


if __name__ == "__main__":
    main()
