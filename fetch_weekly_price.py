# -*- coding: utf-8 -*-
"""
抓取周线股价并生成 ISO 周对齐价格文件（供 weekly_report.py 使用）
用法: python fetch_weekly_price.py <secid> <beg> <end> <out_json>
示例: python fetch_weekly_price.py 116.01810 20240101 20260903 mi_panic_price_aligned.json
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
SECID = sys.argv[1] if len(sys.argv) > 1 else "116.01810"
BEG = sys.argv[2] if len(sys.argv) > 2 else "20240101"
END = sys.argv[3] if len(sys.argv) > 3 else "20260903"
OUT_JSON = sys.argv[4] if len(sys.argv) > 4 else "mi_panic_price_aligned.json"

url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={SECID}"
       f"&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1,f2,f3,f4,f5,f6"
       f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
       f"&klt=102&fqt=1&beg={BEG}&end={END}")
cmd = ["curl", "-s", "-m", "30", url, "-H", "User-Agent: Mozilla/5.0", "--compressed"]
out = subprocess.run(cmd, capture_output=True, timeout=35)
d = json.loads(out.stdout.decode("utf-8", errors="ignore"))
klines = d.get("data", {}).get("klines", [])
print(f"抓取 {len(klines)} 条周线")


def iso_week(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


result = []
for k in klines:
    parts = k.split(",")
    wk = iso_week(parts[0])
    result.append({"week_start": wk, "price": round(float(parts[2]), 2)})

with open(os.path.join(BASE, "data", OUT_JSON), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"生成 {len(result)} 周对齐价格，已保存 {OUT_JSON}")
print("=== 最近 5 周 ===")
for r in result[-5:]:
    print(f"  {r['week_start']} -> {r['price']}")
