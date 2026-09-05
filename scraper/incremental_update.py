# -*- coding: utf-8 -*-
"""
增量抓取：抓取最近 N 页，收集 publish_time >= SINCE 的帖子，
按 post_id 去重后追加到现有 jsonl。
用法: python incremental_update.py <code> <SINCE> <hist_jsonl> [max_pages]
示例: python incremental_update.py hk01810 2026-09-01 eastmoney_history.jsonl 80
"""
import json
import subprocess
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://gbapi.eastmoney.com/webarticlelist/api/Article/WebArticleList"
UA_WAP = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 " \
         "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = sys.argv[1] if len(sys.argv) > 1 else "hk01810"
SINCE = sys.argv[2] if len(sys.argv) > 2 else "2026-09-01"
HIST = sys.argv[3] if len(sys.argv) > 3 else "eastmoney_history.jsonl"
MAX_PAGES = int(sys.argv[4]) if len(sys.argv) > 4 else 80

HIST_FILE = os.path.join(BASE, "data", HIST)


def curl_page(page: int) -> dict:
    url = (f"{API}?code={CODE}&p={page}&ps=50&sorttype=1&plat=wap"
           f"&version=300&product=guba&deviceid=1&ctoken=undefined&utoken=undefined")
    for _ in range(3):
        try:
            cmd = ["curl", "-s", "-m", "25", url,
                   "-H", f"User-Agent: {UA_WAP}",
                   "-H", "Accept: application/json, text/plain, */*", "--compressed"]
            out = subprocess.run(cmd, capture_output=True, timeout=30)
            return json.loads(out.stdout.decode("utf-8", errors="ignore"))
        except Exception:
            time.sleep(0.8)
    return {}


def fetch_page(page):
    time.sleep(0.06 * (page % 5))
    d = curl_page(page)
    relist = d.get("re", [])
    rows = []
    for p in relist:
        pt = p.get("post_publish_time") or ""
        if pt[:10] >= SINCE:
            rows.append({
                "post_id": p.get("post_id"),
                "title": p.get("post_title") or "",
                "content": p.get("post_content") or "",
                "publish_time": pt,
                "read": p.get("post_click_count") or 0,
                "reply": p.get("post_comment_count") or 0,
                "post_type": p.get("post_type") or 0,
                "author": (p.get("post_user") or {}).get("user_nickname", ""),
            })
    return page, rows


def main():
    # 载入已有 post_id 集合（去重）
    existing = set()
    if os.path.exists(HIST_FILE):
        with open(HIST_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    p = json.loads(line)
                    if p.get("post_id") is not None:
                        existing.add(str(p["post_id"]))
                except Exception:
                    continue
    print(f"现有 {len(existing)} 个 post_id")

    new_rows = []
    seen = set()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_page, p): p for p in range(1, MAX_PAGES + 1)}
        for fut in as_completed(futs):
            page, rows = fut.result()
            for r in rows:
                pid = str(r["post_id"])
                if pid in existing or pid in seen:
                    continue
                seen.add(pid)
                new_rows.append(r)

    # 按发布时间排序后追加
    new_rows.sort(key=lambda x: x["publish_time"])
    if new_rows:
        with open(HIST_FILE, "a", encoding="utf-8") as f:
            for r in new_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"新增 {len(new_rows)} 条帖子（>= {SINCE}）")
    from collections import Counter
    c = Counter(r["publish_time"][:10] for r in new_rows)
    for d in sorted(c):
        print(f"  {d}: {c[d]}")


if __name__ == "__main__":
    main()
