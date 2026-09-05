# -*- coding: utf-8 -*-
"""
恐慌指数主流程
1. 加载东财 + 雪球帖子数据
2. NLP 情感分析
3. 计算恐慌指数
4. 输出结果 JSON
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nlp.sentiment import analyze_post
from index.panic_index import load_and_compute, compute_panic, compute_stats, group_by_day

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")


MEDIA_AUTHOR_SUFFIX = ("资讯", "报道", "观察", "财经社", "财讯社", "新闻", "直播", "前沿", "公社", "翻译官")


def is_media_post(p: dict) -> bool:
    """判断是否为资讯/自媒体帖（非散户观点）"""
    author = p.get("author", "")
    text = (p.get("title", "") + " " + p.get("content", ""))
    if any(s in author for s in MEDIA_AUTHOR_SUFFIX):
        return True
    if any(k in text for k in ("邀您观看", "邀您", "锁定", "请点击标题", "完整早报")):
        return True
    return False


def analyze_file(path: str, source: str) -> list:
    """对帖子文件做情感分析，返回带标签的帖子列表
    东财数据：过滤资讯帖(post_type=1)、公告(post_type=3)及自媒体转载
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    results = []
    skipped = 0
    for p in raw:
        if source == "eastmoney":
            pt = p.get("post_type", 0)
            if pt in (1, 3):  # 剔除资讯/公告
                skipped += 1
                continue
            if pt == 20 and is_media_post(p):  # 剔除自媒体转载
                skipped += 1
                continue
        r = analyze_post(p)
        r["source"] = source
        results.append(r)
    if skipped:
        print(f"  已过滤 {skipped} 条资讯/公告/自媒体帖")
    return results


def main():
    em_path = os.path.join(DATA, "eastmoney_posts.json")
    xq_path = os.path.join(DATA, "xueqiu_posts_raw.json")

    posts = []
    if os.path.exists(em_path):
        em = analyze_file(em_path, "eastmoney")
        posts.extend(em)
        print(f"东财帖子: {len(em)} 条")
    else:
        print("[warn] 未找到东财数据文件")

    if os.path.exists(xq_path):
        xq = analyze_file(xq_path, "xueqiu")
        posts.extend(xq)
        print(f"雪球帖子: {len(xq)} 条")

    if not posts:
        print("无数据，退出")
        return

    # 计算恐慌指数
    stats = compute_stats(posts)
    panic = compute_panic(posts)
    daily = group_by_day(posts)

    # 保存结果
    result = {
        "panic_index": panic,
        "daily": daily,
        "posts": posts,
    }
    out = os.path.join(DATA, "result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n=== 恐慌指数结果 ===")
    print(f"恐慌指数: {panic['panic_index']} ({panic['level']})")
    print(f"总帖子: {stats['total']} | 看多: {stats['bull']} | 看空: {stats['bear']} | 中性: {stats['neutral']}")
    print(f"看空/看多比: {stats['bear_ratio']} | 情感均值: {stats['mean_strength']}")
    print(f"结果已保存: {out}")


if __name__ == "__main__":
    main()
