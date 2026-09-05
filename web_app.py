# -*- coding: utf-8 -*-
"""
恐慌指数 Web 服务
- 输入港股/A股代码，输出 100 周恐慌指数
- 前端：web/index.html
- 接口：
    GET  /                         → 前端页面
    POST /api/start                → 启动抓取任务 {code}
    GET  /api/progress/{task_id}   → 查询进度
    GET  /api/result/{task_id}     → 查询结果
"""
import json
import os
import sys
import threading
import uuid
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from scraper.eastmoney_history_scraper import scrape, curl_page
from weekly_analysis import load_and_analyze, compute_weekly_panic

app = FastAPI(title="恐慌指数 Web 服务")

# 任务状态表
TASKS = {}
START_DATE = "2024-09-17"  # 100 周前


def parse_code(raw: str):
    """解析股票代码，返回 (东财code, 市场, 股票名)"""
    raw = raw.strip().upper()
    for suf in (".SH", ".SZ", ".SS", ".HK", ".US"):
        raw = raw.replace(suf, "")
    raw = raw.strip()

    # 去掉可能的 hk 前缀先保留判断
    is_hk = raw.startswith("HK")
    digits = "".join(c for c in raw if c.isdigit())

    if is_hk or 3 <= len(digits) <= 5:
        code = "hk" + digits.zfill(5)
        market = "港股"
    elif len(digits) == 6:
        code = digits
        market = "A股"
    else:
        raise ValueError(f"无法识别的股票代码: {raw}（A股6位，港股5位）")

    # 拿股票名
    name = code
    try:
        d = curl_page(1, code=code)
        name = (d.get("bar_info") or {}).get("ShortName", code)
    except Exception:
        pass
    return code, market, name


def run_task(task_id: str, code: str, market: str, name: str):
    """后台任务：抓取 → 分析 → 计算"""
    state = TASKS[task_id]
    prefix = f"web_{task_id[:8]}"

    def progress_cb(done, total):
        if done == -1:
            state["stage"] = "探测目标页数"
            state["progress"] = 3
        elif total > 0:
            state["stage"] = f"抓取帖子（{done}/{total} 页）"
            state["progress"] = 5 + (done / total) * 80

    try:
        # 1. 抓取
        state["stage"] = "抓取帖子"
        scrape(code, START_DATE, prefix, progress_cb=progress_cb, concurrency=8)

        # 2. 分析
        state["stage"] = "情感分析"
        state["progress"] = 88
        hist_file = os.path.join(BASE, "data", f"{prefix}_history.jsonl")
        weeks = load_and_analyze(hist_file)

        # 3. 计算
        state["stage"] = "计算恐慌指数"
        state["progress"] = 95
        weekly = compute_weekly_panic(weeks)

        state["status"] = "done"
        state["progress"] = 100
        state["stage"] = "完成"
        state["result"] = {
            "code": code,
            "market": market,
            "name": name,
            "weekly": weekly,
        }
    except Exception as e:
        state["status"] = "error"
        state["message"] = str(e)


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = os.path.join(BASE, "web", "index.html")
    with open(html_file, encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/start")
async def start(req: Request):
    body = await req.json()
    raw = body.get("code", "")
    if not raw:
        return JSONResponse({"error": "请输入股票代码"}, status_code=400)
    try:
        code, market, name = parse_code(raw)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    task_id = uuid.uuid4().hex
    TASKS[task_id] = {
        "task_id": task_id,
        "status": "running",
        "stage": "初始化",
        "progress": 0,
        "code": code,
        "market": market,
        "name": name,
        "result": None,
    }
    t = threading.Thread(target=run_task, args=(task_id, code, market, name), daemon=True)
    t.start()
    return JSONResponse({
        "task_id": task_id,
        "code": code,
        "market": market,
        "name": name,
    })


@app.get("/api/progress/{task_id}")
def progress(task_id: str):
    state = TASKS.get(task_id)
    if not state:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    return JSONResponse({
        "status": state["status"],
        "stage": state["stage"],
        "progress": state["progress"],
        "name": state["name"],
        "market": state["market"],
        "message": state.get("message", ""),
    })


@app.get("/api/result/{task_id}")
def result(task_id: str):
    state = TASKS.get(task_id)
    if not state:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    if state["status"] != "done":
        return JSONResponse({"error": "任务尚未完成", "progress": state["progress"]}, status_code=409)
    return JSONResponse(state["result"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
