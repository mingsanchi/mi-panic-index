# -*- coding: utf-8 -*-
"""
生成「近 N 天恐慌指数」HTML 报告
用法: python daily_report.py <输入json> <窗口描述> <股票名> <代码> <输出html>
示例: python daily_report.py mi_90days.json "90 天" "小米集团-W" "01810.HK" mi_90days_report.html
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
IN_FILE = sys.argv[1] if len(sys.argv) > 1 else "mi_30workdays.json"
WIN_LABEL = sys.argv[2] if len(sys.argv) > 2 else "30 个工作日"
STOCK_NAME = sys.argv[3] if len(sys.argv) > 3 else "小米集团-W"
STOCK_CODE = sys.argv[4] if len(sys.argv) > 4 else "01810.HK"
OUT_HTML = sys.argv[5] if len(sys.argv) > 5 else "mi_30workdays_report.html"
PRICE_FILE = sys.argv[6] if len(sys.argv) > 6 else "mi_90days_price.json"

with open(os.path.join(BASE, "data", IN_FILE), encoding="utf-8") as f:
    D = json.load(f)

dates = [r["date"][5:] for r in D]
panics = [r["panic"] for r in D]
totals = [r["total"] for r in D]
bulls = [r["bull"] for r in D]
bears = [r["bear"] for r in D]
bear_ratios = [round(r["bear_ratio"] * 100, 1) for r in D]
strengths = [r["mean_strength"] for r in D]

# 股价（日线收盘价，交易日有值、休市日为 null）
prices = [None] * len(D)
_price_file = os.path.join(BASE, "data", PRICE_FILE)
_pmap = {}
if os.path.exists(_price_file):
    with open(_price_file, encoding="utf-8") as f:
        _pd = json.load(f)
    _pmap = {p["date"]: p["price"] for p in _pd}
    prices = [round(_pmap[r["date"]], 2) if r["date"] in _pmap else None for r in D]
has_price = any(p is not None for p in prices)

# 对齐：只保留有股价的交易日，确保 x 轴日期、恐慌指数、股价严格一一对应
if has_price:
    _idx = [i for i, p in enumerate(prices) if p is not None]
    D = [D[i] for i in _idx]
    dates = [dates[i] for i in _idx]
    panics = [panics[i] for i in _idx]
    totals = [totals[i] for i in _idx]
    bulls = [bulls[i] for i in _idx]
    bears = [bears[i] for i in _idx]
    bear_ratios = [bear_ratios[i] for i in _idx]
    strengths = [strengths[i] for i in _idx]
    prices = [prices[i] for i in _idx]

cur = D[-1]
max_r = max(D, key=lambda r: r["panic"])
min_r = min(D, key=lambda r: r["panic"])
avg_p = round(sum(panics) / len(panics), 1)
avg_br = round(sum(r["bear_ratio"] for r in D) / len(D) * 100, 1)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{STOCK_NAME} 恐慌指数 · 近 {WIN_LABEL}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  :root {{ --bg:#f7f8fa; --card:#fff; --text:#1f2329; --sub:#646a73; --line:#e5e6eb; --red:#e03a3a; --green:#1a9e5c; --accent:#2b6de8; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.6; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:24px 20px 60px; }}
  h1 {{ font-size:24px; font-weight:700; }}
  .sub {{ color:var(--sub); font-size:13px; margin-top:4px; }}
  .hero {{ display:flex; gap:14px; flex-wrap:wrap; margin-top:16px; }}
  .stat {{ flex:1 1 180px; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; text-align:center; }}
  .stat .v {{ font-size:30px; font-weight:800; }}
  .stat .k {{ font-size:12px; color:var(--sub); margin-top:4px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:20px 24px; margin-top:16px; }}
  .card h2 {{ font-size:16px; font-weight:600; margin-bottom:12px; }}
  .chart {{ height:380px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media (max-width:760px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th,td {{ padding:6px 8px; border-bottom:1px solid var(--line); text-align:left; }}
  th {{ color:var(--sub); font-weight:500; background:#fafbfc; }}
  .red {{ color:var(--red); }} .green {{ color:var(--green); }}
  .disc {{ font-size:12px; color:var(--sub); border-top:1px solid var(--line); margin-top:20px; padding-top:14px; }}
  .src {{ font-size:12px; color:var(--sub); }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{STOCK_NAME} 散户恐慌指数 · 近 {WIN_LABEL}</h1>
  <div class="sub">标的：{STOCK_NAME}（{STOCK_CODE}）｜数据源：东方财富股吧｜周期：{D[0]['date']} ~ {D[-1]['date']}（近 {WIN_LABEL} 内 {len(D)} 个交易日）｜共 {sum(totals):,} 条用户帖</div>

  <div class="hero">
    <div class="stat"><div class="v" style="color:{'var(--green)' if cur['panic']>0 else 'var(--red)'};">{cur['panic']}</div><div class="k">最新（{cur['date']}）</div></div>
    <div class="stat"><div class="v">{avg_p}</div><div class="k">30 日均值</div></div>
    <div class="stat"><div class="v">{avg_br}%</div><div class="k">看空占比均值</div></div>
    <div class="stat"><div class="v green">{max_r['panic']}</div><div class="k">最高恐慌（{max_r['date']}）</div></div>
    <div class="stat"><div class="v red">{min_r['panic']}</div><div class="k">最低（{min_r['date']}）</div></div>
  </div>

  <div class="card">
    <h2>恐慌指数 vs 股价走势（蓝=恐慌左轴，红=股价右轴）</h2>
    <div id="panic" class="chart"></div>
  </div>

  <div class="card">
    <h2>看空占比与发帖量</h2>
    <div class="grid2">
      <div id="ratio" class="chart" style="height:300px;"></div>
      <div id="volume" class="chart" style="height:300px;"></div>
    </div>
  </div>

  <div class="card">
    <h2>{WIN_LABEL}明细</h2>
    <table>
      <tr><th>日期</th><th>恐慌指数</th><th>发帖量</th><th>看多</th><th>看空</th><th>中性</th><th>看空占比</th><th>情感均值</th></tr>
      {"".join(f"<tr><td>{r['date']}</td><td><b class=\"{'green' if r['panic']>0 else 'red'}\">{r['panic']}</b></td><td>{r['total']}</td><td>{r['bull']}</td><td>{r['bear']}</td><td>{r['neutral']}</td><td>{round(r['bear_ratio']*100)}%</td><td>{r['mean_strength']}</td></tr>" for r in D)}
    </table>
  </div>

  <div class="card">
    <h2>方法论与数据说明</h2>
    <p class="src">
      ① 指数公式：<b>Panic = 看空帖数 × (0.2 − 情感均值) / 0.2</b>，按交易日逐日计算；正数=恐慌、负数=乐观。<br>
      ② 情感均值 = 热度加权的单帖看多/看空强度（−1 ~ +1），权重 w = 1 + √(阅读 + 2×评论)；看空帖数 = 词典法判为"看空"的帖子数。<br>
      ③ NLP：金融看多/看空词典法，匹配看多词（涨停/抄底/利好…）与看空词（跌停/割肉/活埋…）。<br>
      ④ 数据源：东方财富股吧「{STOCK_NAME}吧」移动端接口，已剔除资讯帖、公告及自媒体转载。<br>
      ⑤ 局限：词典法对长文/反讽有误判；单日样本量波动较大（200~1400 帖）；情绪温度计不代表股价涨跌方向。
    </p>
  </div>

  <p class="disc"><b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。</p>
</div>

<script>
var dates = {json.dumps(dates)};
var panics = {json.dumps(panics)};
var totals = {json.dumps(totals)};
var bearRatios = {json.dumps(bear_ratios)};
var prices = {json.dumps(prices)};

echarts.init(document.getElementById('panic')).setOption({{
  tooltip: {{ trigger:'axis', formatter:function(p){{ var s = p[0].name; var out = s; p.forEach(function(it){{ if(it.seriesName==='恐慌指数') out += '<br>恐慌指数: ' + it.value; if(it.seriesName==='股价') out += '<br>股价: ' + it.value; }}); return out; }} }},
  grid: {{ left:50, right:55, top:30, bottom:60 }},
  xAxis: {{ type:'category', data:dates, boundaryGap:false, axisLabel:{{ rotate:60, fontSize:10 }} }},
  yAxis: [
    {{ type:'value', min:0, name:'恐慌指数', position:'left' }},
    {{ type:'value', min:20, name:'股价(HK$)', position:'right' }}
  ],
  series: [{{
    name:'恐慌指数', type:'line', data:panics, smooth:true, yAxisIndex:0,
    lineStyle:{{ width:2.5, color:'#2b6de8' }}, itemStyle:{{ color:'#2b6de8' }}, areaStyle:{{ color:'rgba(43,109,232,0.06)' }},
    markLine:{{ data:[{{ yAxis:0 }}], lineStyle:{{ type:'dashed', color:'#999' }}, label:{{ formatter:'多空分界 0' }} }}
  }},{{
    name:'股价', type:'line', data:prices, smooth:true, yAxisIndex:1,
    lineStyle:{{ width:2, color:'#e03a3a' }}, itemStyle:{{ color:'#e03a3a' }},
    connectNulls:true
  }}]
}});

echarts.init(document.getElementById('ratio')).setOption({{
  tooltip:{{ trigger:'axis', formatter:function(p){{ return p[0].name + ': 看空占比 ' + p[0].value + '%'; }} }},
  grid:{{ left:40, right:20, top:30, bottom:60 }},
  xAxis:{{ type:'category', data:dates, boundaryGap:false, axisLabel:{{ rotate:60, fontSize:10 }} }},
  yAxis:{{ type:'value', min:0, max:100, name:'看空占比(%)' }},
  series:[{{ type:'line', data:bearRatios, smooth:true, lineStyle:{{ color:'#1a9e5c', width:2 }}, itemStyle:{{ color:'#1a9e5c' }},
    markLine:{{ data:[{{ yAxis:50 }}], lineStyle:{{ type:'dashed', color:'#999' }}, label:{{ formatter:'多空平衡 50%' }} }} }}]
}});

echarts.init(document.getElementById('volume')).setOption({{
  tooltip:{{ trigger:'axis' }},
  grid:{{ left:50, right:20, top:30, bottom:60 }},
  xAxis:{{ type:'category', data:dates, axisLabel:{{ rotate:60, fontSize:10 }} }},
  yAxis:{{ type:'value', name:'发帖量' }},
  series:[{{ type:'bar', data:totals, itemStyle:{{ color:'#2b6de8' }} }}]
}});
</script>
</body>
</html>
"""

out = os.path.join(BASE, "output", OUT_HTML)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"报告已生成: {out}")
print(f"周期 {D[0]['date']} ~ {D[-1]['date']}, 共 {len(D)} 天")
