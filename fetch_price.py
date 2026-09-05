# -*- coding: utf-8 -*-
"""
抓取日线股价并生成与恐慌指数对齐的价格文件
用法: python fetch_price.py <secid> <start> <end> <panic_json> <out_json>
示例: python fetch_price.py 116.01810 20260601 20260903 mi_90days.json mi_90days_price.json
"""
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SECID = sys.argv[1] if len(sys.argv) > 1 else "116.01810"
BEG = sys.argv[2] if len(sys.argv) > 2 else "20260601"
END = sys.argv[3] if len(sys.argv) > 3 else "20260903"
PANIC_JSON = sys.argv[4] if len(sys.argv) > 4 else "mi_90days.json"
OUT_JSON = sys.argv[5] if len(sys.argv) > 5 else "mi_90days_price.json"

url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={SECID}"
       f"&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1,f2,f3,f4,f5,f6"
       f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
       f"&klt=101&fqt=1&beg={BEG}&end={END}")
cmd = ["curl", "-s", "-m", "30", url, "-H", "User-Agent: Mozilla/5.0", "--compressed"]
out = subprocess.run(cmd, capture_output=True, timeout=35)
d = json.loads(out.stdout.decode("utf-8", errors="ignore"))
klines = d.get("data", {}).get("klines", [])
print(f"抓取 {len(klines)} 条 K 线")

# 收盘价映射（f53 = 收盘价）
pmap = {}
for k in klines:
    parts = k.split(",")
    pmap[parts[0]] = round(float(parts[2]), 2)

# 合并恐慌数据
with open(os.path.join(BASE, "data", PANIC_JSON), encoding="utf-8") as f:
    panic_data = json.load(f)

merged = []
for r in panic_data:
    if r["date"] in pmap:
        merged.append({
            "date": r["date"],
            "panic": r["panic"],
            "price": pmap[r["date"]],
            "bear_ratio": r["bear_ratio"],
            "total": r["total"],
        })

with open(os.path.join(BASE, "data", OUT_JSON), "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f"对齐 {len(merged)} 个交易日，已保存 {OUT_JSON}")
print("=== 最近 5 个交易日 ===")
for m in merged[-5:]:
    print(f"  {m['date']} | 收盘 {m['price']} | panic {m['panic']}")
