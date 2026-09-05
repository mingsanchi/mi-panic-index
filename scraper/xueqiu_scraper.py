# -*- coding: utf-8 -*-
"""
雪球讨论抓取器 —— 小米集团-W (01810.HK)
通过 playwright 加载 cookie + 拦截 search/status.json 响应拿到帖子 JSON
- 打开纯净搜索 URL（不带 type/sortId/page 参数，避免被识别）
- 滚动页面触发"加载更多"翻页
- 拦截响应解析 list
"""
import json
import time
import os
import re
from playwright.sync_api import sync_playwright
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_FILE = os.path.join(BASE, "data", "xueqiu_cookies.json")
OUT_FILE = os.path.join(BASE, "data", "xueqiu_posts.jsonl")
KEYWORD = "小米集团-W"


def load_cookies():
    with open(COOKIE_FILE, encoding="utf-8") as f:
        return json.load(f)


def parse_status(s: dict) -> dict:
    user = s.get("user") or {}
    created_ms = s.get("created_at", 0)
    ts = datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d %H:%M:%S") if created_ms else ""
    text = s.get("text", "") or s.get("description", "") or ""
    text_clean = re.sub(r"<[^>]+>", " ", text)
    text_clean = re.sub(r"\s+", " ", text_clean).strip()
    return {
        "post_id": str(s.get("id", "")),
        "title": s.get("title", "") or "",
        "content": text_clean,
        "publish_time": ts,
        "read": s.get("view_count", 0) or 0,
        "reply": s.get("reply_count", 0) or 0,
        "like": s.get("like_count", 0) or 0,
        "retweet": s.get("retweet_count", 0) or 0,
        "author": user.get("screen_name", ""),
        "source": "xueqiu",
    }


def scrape(max_scrolls: int = 30, scroll_wait: float = 4.0):
    cookies = load_cookies()
    all_posts = []
    seen_ids = set()

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_cookies(cookies)
        pg = ctx.new_page()

        captured = []

        def on_response(resp):
            if "search/status.json" in resp.url and resp.status == 200:
                try:
                    body = resp.text()
                    if len(body) > 1000:  # 有效数据
                        j = json.loads(body)
                        captured.append(j)
                except Exception:
                    pass

        pg.on("response", on_response)

        pg.goto(f"https://xueqiu.com/k?q={KEYWORD}", wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_timeout(7000)

        for i in range(max_scrolls):
            before = len(captured)
            pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            pg.wait_for_timeout(int(scroll_wait * 1000))
            new = len(captured) - before
            # 从新捕获的响应提取帖子
            added = 0
            for j in captured[before:]:
                statuses = j.get("list") or j.get("statuses") or []
                for s in statuses:
                    post = parse_status(s)
                    if post["post_id"] and post["post_id"] not in seen_ids:
                        seen_ids.add(post["post_id"])
                        all_posts.append(post)
                        added += 1
            print(f"  滚动{i+1}: 新响应{new}个, 新增{added}条, 累计{len(all_posts)}条", flush=True)
            if added == 0 and new == 0 and i >= 3:
                print("  连续无新数据，停止", flush=True)
                break

        b.close()

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for post in all_posts:
            f.write(json.dumps(post, ensure_ascii=False) + "\n")
    print(f"\n完成！共 {len(all_posts)} 条 → {OUT_FILE}", flush=True)
    return all_posts


if __name__ == "__main__":
    scrape()