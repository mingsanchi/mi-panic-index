# -*- coding: utf-8 -*-
"""
东方财富股吧抓取器 —— 小米集团-W (hk01810)
使用 WAP 移动端 JSON API（免验证码，直接返回标题+正文+阅读/评论数）
"""
import json
import time
import subprocess

API = "https://gbapi.eastmoney.com/webarticlelist/api/Article/WebArticleList"
UA_WAP = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 " \
         "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

CODE = "hk01810"  # 小米集团-W


def curl_json(url: str, timeout: int = 20) -> dict:
    cmd = ["curl", "-s", "-m", str(timeout), url,
           "-H", f"User-Agent: {UA_WAP}",
           "-H", "Accept: application/json, text/plain, */*",
           "--compressed"]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
        return json.loads(out.stdout.decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"    [curl error] {e}")
        return {}


def build_url(page: int, ps: int = 50) -> str:
    return (f"{API}?code={CODE}&p={page}&ps={ps}&sorttype=1&plat=wap"
            f"&version=300&product=guba&deviceid=1&ctoken=undefined&utoken=undefined")


def fetch_page(page: int, ps: int = 50) -> list:
    """抓取一页，返回规范化帖子列表（含正文）"""
    data = curl_json(build_url(page, ps))
    relist = data.get("re", [])
    posts = []
    for r in relist:
        user = r.get("post_user") or {}
        posts.append({
            "postid": str(r.get("post_id", "")),
            "title": (r.get("post_title") or "").strip(),
            "content": (r.get("post_content") or "").strip(),
            "author": user.get("user_nickname", ""),
            "read": int(r.get("post_click_count") or 0),
            "reply": int(r.get("post_comment_count") or 0),
            "like": int(r.get("post_like_count") or 0),
            "publish_time": r.get("post_publish_time", ""),
            "post_type": int(r.get("post_type") or 0),   # 1=资讯帖, 0=用户帖
            "top_status": int(r.get("post_top_status") or 0),
        })
    return posts


def scrape(pages: int = 10, ps: int = 50, sleep: float = 1.2) -> list:
    """抓取多页，返回帖子列表"""
    all_posts = []
    seen = set()
    for p in range(1, pages + 1):
        posts = fetch_page(p, ps)
        new_cnt = 0
        for post in posts:
            if post["postid"] in seen:
                continue
            seen.add(post["postid"])
            all_posts.append(post)
            new_cnt += 1
        print(f"  第{p}页: 获取{len(posts)}条, 新增{new_cnt}条, 累计{len(all_posts)}条")
        if new_cnt == 0:
            print("  无新增，停止翻页")
            break
        time.sleep(sleep)
    return all_posts


if __name__ == "__main__":
    import os
    posts = scrape(pages=10, ps=50)
    out_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "data", "eastmoney_posts.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(posts)} 条到 {out_path}")
