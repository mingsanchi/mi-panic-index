# -*- coding: utf-8 -*-
"""
东方财富股吧 100 周历史帖子并发抓取器（通用）
用法: python eastmoney_history_scraper.py <code> <start_date> <out_prefix>
示例: python eastmoney_history_scraper.py 601933 2024-09-17 yonghui
- 使用 WAP JSON API（免验证码）
- 深页 ps 强制 50 条/页
- 并发抓取 + 断点续传 + jsonl 流式存储
- 目标：抓取 publish_time >= START_DATE 的所有帖子
"""
import json
import time
import subprocess
import threading
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API = "https://gbapi.eastmoney.com/webarticlelist/api/Article/WebArticleList"
UA_WAP = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 " \
         "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

PS = 50  # 深页固定 50 条/页
CONCURRENCY = 5

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CODE = sys.argv[1] if len(sys.argv) > 1 else "601933"
START_DATE = sys.argv[2] if len(sys.argv) > 2 else "2024-09-17"
PREFIX = sys.argv[3] if len(sys.argv) > 3 else "yonghui"

OUT_FILE = os.path.join(BASE, "data", f"{PREFIX}_history.jsonl")
DONE_FILE = os.path.join(BASE, "data", f"{PREFIX}_done_pages.txt")

write_lock = threading.Lock()
done_pages = set()


def curl_page(page: int, retry: int = 2, code: str = None) -> dict:
    c = code or CODE
    url = (f"{API}?code={c}&p={page}&ps={PS}&sorttype=1&plat=wap"
           f"&version=300&product=guba&deviceid=1&ctoken=undefined&utoken=undefined")
    for _ in range(retry + 1):
        try:
            cmd = ["curl", "-s", "-m", "25", url,
                   "-H", f"User-Agent: {UA_WAP}",
                   "-H", "Accept: application/json, text/plain, */*", "--compressed"]
            out = subprocess.run(cmd, capture_output=True, timeout=30)
            return json.loads(out.stdout.decode("utf-8", errors="ignore"))
        except Exception:
            time.sleep(1.0)
    return {}


def probe_max_page() -> int:
    """二分探测：找到 publish_time >= START_DATE 的最大页数（50条/页）"""
    def earliest(page):
        d = curl_page(page)
        times = [r.get("post_publish_time", "")[:10] for r in d.get("re", []) if r.get("post_publish_time")]
        return min(times) if times else "9999"

    # 先找上界
    hi, lo = 1, 1
    while True:
        t = earliest(hi)
        if t < START_DATE or hi > 20000:
            break
        hi *= 2
    # 二分
    lo = hi // 2
    for _ in range(20):
        mid = (lo + hi) // 2
        t = earliest(mid)
        if t >= START_DATE:
            lo = mid + 1
        else:
            hi = mid
    return lo


def save_page(page: int, posts: list):
    """保存一页数据（精简字段），jsonl 追加"""
    with write_lock:
        with open(OUT_FILE, "a", encoding="utf-8") as f:
            for p in posts:
                row = {
                    "post_id": p.get("post_id"),
                    "title": p.get("post_title") or "",
                    "content": p.get("post_content") or "",
                    "publish_time": p.get("post_publish_time") or "",
                    "read": p.get("post_click_count") or 0,
                    "reply": p.get("post_comment_count") or 0,
                    "post_type": p.get("post_type") or 0,
                    "author": (p.get("post_user") or {}).get("user_nickname", ""),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        with open(DONE_FILE, "a", encoding="utf-8") as f:
            f.write(f"{page}\n")


def fetch_one(page: int) -> int:
    """抓取单页，返回该页保存的条数"""
    if page in done_pages:
        return 0
    time.sleep(0.08 * (page % 3))  # 轻度错峰
    data = curl_page(page)
    relist = data.get("re", [])
    if not relist:
        return -1  # 空页，标记异常
    # 过滤：只保留 >= START_DATE 的帖子
    valid = [r for r in relist if (r.get("post_publish_time") or "")[:10] >= START_DATE]
    save_page(page, valid)
    return len(valid)


def load_done():
    global done_pages
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE) as f:
            done_pages = set(int(x) for x in f.read().split() if x.strip().isdigit())


def scrape(code, start_date, prefix, progress_cb=None, concurrency=8):
    """抓取指定股票 100 周历史帖子，返回统计 dict
    progress_cb(done, total) 用于进度回调
    """
    global CODE, START_DATE, OUT_FILE, DONE_FILE, done_pages
    CODE = code
    START_DATE = start_date
    OUT_FILE = os.path.join(BASE, "data", f"{prefix}_history.jsonl")
    DONE_FILE = os.path.join(BASE, "data", f"{prefix}_done_pages.txt")
    done_pages = set()

    # 清理旧文件
    if os.path.exists(OUT_FILE):
        os.remove(OUT_FILE)
    if os.path.exists(DONE_FILE):
        os.remove(DONE_FILE)

    # 探测目标页数
    if progress_cb:
        progress_cb(-1, 0)  # -1 表示"探测中"
    max_page = probe_max_page()

    todo = list(range(1, max_page + 1))
    total = len(todo)
    done_cnt = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(fetch_one, p): p for p in todo}
        for fut in as_completed(futures):
            fut.result()
            done_cnt += 1
            if progress_cb and done_cnt % 20 == 0:
                progress_cb(done_cnt, total)

    # 统计
    n_posts = 0
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            n_posts = sum(1 for _ in f)

    return {
        "code": code,
        "start_date": start_date,
        "prefix": prefix,
        "pages": max_page,
        "posts": n_posts,
        "elapsed_sec": round(time.time() - start, 1),
        "out_file": OUT_FILE,
    }


def main():
    scrape(CODE, START_DATE, PREFIX)
    print(f"完成! 输出 {OUT_FILE}")


if __name__ == "__main__":
    main()
