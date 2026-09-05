# -*- coding: utf-8 -*-
"""
生成 100 周恐慌指数 HTML 报告
公式：Panic = 看空帖数 × (0.2 - 情感均值) / 0.2
用法: python weekly_report.py <股票名> <输入json> <输出html>
示例: python weekly_report.py "永辉超市" yonghui_weekly.json yonghui_panic_report.html
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
STOCK_NAME = sys.argv[1] if len(sys.argv) > 1 else "小米集团-W"
STOCK_CODE = sys.argv[2] if len(sys.argv) > 2 else "01810.HK"
IN_FILE = sys.argv[3] if len(sys.argv) > 3 else "weekly_panic.json"
OUT_HTML = sys.argv[4] if len(sys.argv) > 4 else "weekly_panic_report.html"
PRICE_FILE = sys.argv[5] if len(sys.argv) > 5 else "mi_panic_price_aligned.json"

with open(os.path.join(BASE, "data", IN_FILE), encoding="utf-8") as f:
    W = json.load(f)

# 区分：最近 100 个完整周 + 本周（进行中）
COMPLETE = W[-101:-1] if len(W) > 101 else W[:-1]
CURRENT = W[-1]             # 本周（进行中）
weeks = [w["week_start"] for w in COMPLETE]
panics = [w["panic"] for w in COMPLETE]
totals = [w["total"] for w in COMPLETE]
bulls = [w["bull"] for w in COMPLETE]
bears = [w["bear"] for w in COMPLETE]
bear_ratios = [round(w["bear_ratio"] * 100, 1) for w in COMPLETE]
strengths = [round(w["mean_strength"], 3) for w in COMPLETE]

# 股价（东财周线收盘价，已按 ISO 周对齐）
prices = [None] * len(COMPLETE)
_price_file = os.path.join(BASE, "data", PRICE_FILE)
if os.path.exists(_price_file):
    with open(_price_file, encoding="utf-8") as f:
        _pd = json.load(f)
    _pmap = {p["week_start"]: p["price"] for p in _pd}
    prices = [round(_pmap[w], 2) if w in _pmap else None for w in weeks]
has_price = any(p is not None for p in prices)

cur = CURRENT
all_panics = sorted(w["panic"] for w in COMPLETE)
pct = sum(1 for p in all_panics if p <= cur["panic"]) / len(all_panics) * 100
max_w = max(COMPLETE, key=lambda w: w["panic"])
min_w = min(COMPLETE, key=lambda w: w["panic"])
extreme_weeks = sum(1 for w in COMPLETE if w["level"] == "极度恐慌")
high_weeks = sum(1 for w in COMPLETE if w["level"] == "高恐慌")
panic_weeks = sum(1 for w in COMPLETE if w["level"] == "恐慌")
cautious_weeks = sum(1 for w in COMPLETE if w["level"] == "中性偏谨慎")
mild_weeks = sum(1 for w in COMPLETE if w["level"] == "温和")
total_posts = sum(totals)
# panic 分位数（用于走势图着色）
_n = len(all_panics)
_q20 = all_panics[int(_n * 0.2)]
_q50 = all_panics[int(_n * 0.5)]
_q80 = all_panics[int(_n * 0.8)]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def panic_cell(v):
    """恐慌指数带符号 + 颜色"""
    if v > 0:
        return f'<span class="green">+{v:.1f}</span>'
    elif v < 0:
        return f'<span class="red">{v:.1f}</span>'
    return '<span style="color:#999;">0.0</span>'


# 明细表（100 完整周 + 本周）
detail_rows = "".join(
    f"<tr><td>{w['week_start']}</td><td>{panic_cell(w['panic'])}</td>"
    f"<td>{w['level']}</td><td>{w['total']}</td><td>{w['bull']}</td><td>{w['bear']}</td>"
    f"<td>{round(w['bear_ratio']*100)}%</td><td>{w['mean_strength']}</td></tr>"
    for w in COMPLETE
)
cur_row = (
    f"<tr style=\"background:#f6f8fb;\"><td><b>{CURRENT['week_start']}</b> "
    f"<span style=\"color:#999;\">(进行中)</span></td><td>{panic_cell(CURRENT['panic'])}</td>"
    f"<td>{CURRENT['level']}</td><td>{CURRENT['total']}</td><td>{CURRENT['bull']}</td>"
    f"<td>{CURRENT['bear']}</td><td>{round(CURRENT['bear_ratio']*100)}%</td>"
    f"<td>{CURRENT['mean_strength']}</td></tr>"
)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{STOCK_NAME} 恐慌指数 · 100 周回顾</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  :root {{ --bg:#f7f8fa; --card:#fff; --text:#1f2329; --sub:#646a73; --line:#e5e6eb; --red:#e03a3a; --green:#1a9e5c; --accent:#2b6de8; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.6; }}
  .wrap {{ max-width:1160px; margin:0 auto; padding:24px 20px 60px; }}
  h1 {{ font-size:24px; font-weight:700; }}
  .sub {{ color:var(--sub); font-size:13px; margin-top:4px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:20px 24px; margin-top:16px; }}
  .card h2 {{ font-size:16px; font-weight:600; margin-bottom:12px; }}
  .hero {{ display:flex; gap:16px; flex-wrap:wrap; }}
  .stat {{ flex:1 1 190px; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; text-align:center; }}
  .stat .v {{ font-size:30px; font-weight:800; }}
  .stat .k {{ font-size:12px; color:var(--sub); margin-top:4px; }}
  .chart {{ height:380px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media (max-width:760px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th,td {{ padding:6px 8px; border-bottom:1px solid var(--line); text-align:left; }}
  th {{ color:var(--sub); font-weight:500; background:#fafbfc; position:sticky; top:0; }}
  .red {{ color:var(--red); }} .green {{ color:var(--green); }}
  .disc {{ font-size:12px; color:var(--sub); border-top:1px solid var(--line); margin-top:20px; padding-top:14px; }}
  .src {{ font-size:12px; color:var(--sub); }}
  .scroll {{ max-height:600px; overflow-y:auto; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{STOCK_NAME} 散户恐慌指数 · 100 周回顾</h1>
  <div class="sub">标的：{STOCK_NAME}（{STOCK_CODE}）｜数据源：东方财富股吧｜周期：{weeks[0]} ~ {weeks[-1]}（完整 {len(COMPLETE)} 周）｜共 {total_posts:,} 条用户帖｜本周（{CURRENT['week_start']}）进行中</div>

  <div class="hero">
    <div class="stat"><div class="v" style="color:{'var(--green)' if cur['panic']>0 else 'var(--red)' if cur['panic']<0 else '#999'};">{panic_cell(cur['panic'])}</div><div class="k">本周恐慌指数（{cur['level']}·进行中）</div></div>
    <div class="stat"><div class="v">{pct:.0f}%</div><div class="k">历史分位（高于 {pct:.0f}% 的完整周）</div></div>
    <div class="stat"><div class="v">{cur['total']:,}</div><div class="k">本周发帖量（仅周一）</div></div>
    <div class="stat"><div class="v">{round(cur['bear_ratio']*100)}%</div><div class="k">本周看空占比</div></div>
    <div class="stat"><div class="v">{panic_cell(min_w['panic'])}</div><div class="k">100 周最低（{min_w['week_start']}）</div></div>
    <div class="stat"><div class="v">{panic_cell(max_w['panic'])}</div><div class="k">100 周最高（{max_w['week_start']}）</div></div>
  </div>

  <div class="card">
    <h2>恐慌指数 vs 股价 vs 看空占比 · 100 周走势（蓝=恐慌左轴，红=股价右轴，绿虚线=看空占比最右轴）</h2>
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
    <h2>情感均值（-1 全看空 ~ +1 全看多）</h2>
    <div id="strength" class="chart" style="height:280px;"></div>
  </div>

  <div class="card">
    <h2>100 周情绪分布统计</h2>
    <table>
      <tr><th>维度</th><th>数值</th><th>说明</th></tr>
      <tr><td>极度恐慌周（Panic &gt; 3000）</td><td>{extreme_weeks} 周</td><td>占比 {round(extreme_weeks/len(COMPLETE)*100)}%</td></tr>
      <tr><td>高恐慌周（80% 分位以上）</td><td>{high_weeks} 周</td><td>占比 {round(high_weeks/len(COMPLETE)*100)}%</td></tr>
      <tr><td>恐慌周（50%~80% 分位）</td><td>{panic_weeks} 周</td><td>占比 {round(panic_weeks/len(COMPLETE)*100)}%</td></tr>
      <tr><td>中性偏谨慎周（20%~50% 分位）</td><td>{cautious_weeks} 周</td><td>占比 {round(cautious_weeks/len(COMPLETE)*100)}%</td></tr>
      <tr><td>温和周（后 20% 分位）</td><td>{mild_weeks} 周</td><td>占比 {round(mild_weeks/len(COMPLETE)*100)}%</td></tr>
      <tr><td>周均发帖量</td><td>{round(sum(totals)/len(COMPLETE)):,} 条</td><td>平均每周散户发帖</td></tr>
      <tr><td>看空占比区间</td><td>{min(bear_ratios)}% ~ {max(bear_ratios)}%</td><td>100 周看空占比范围</td></tr>
    </table>
  </div>

  <div class="card">
    <h2>100 周完整明细</h2>
    <div class="scroll">
    <table>
      <tr><th>周起始</th><th>恐慌指数</th><th>方向</th><th>发帖量</th><th>看多</th><th>看空</th><th>看空占比</th><th>情感均值</th></tr>
      {detail_rows}
      {cur_row}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>方法论与数据说明</h2>
    <p class="src">
      ① 指数公式：<b>Panic = 看空帖数 × (0.2 − 情感均值) / 0.2</b>，按 ISO 周聚合；<b>Panic &gt; 3000 判定为"极度恐慌"</b>，其余按分位数分档（高恐慌/恐慌/中性偏谨慎/温和）。<br>
      ② 情感均值 = 热度加权的单帖看多/看空强度（范围 −1 ~ +1），权重 w = 1 + √(阅读 + 2×评论)；看空帖数 = 该周词典法判定为"看空"的帖子数。<br>
      ③ NLP：金融看多/看空词典法（纯规则），对标题+正文匹配看多词（涨停/抄底/利好…）与看空词（跌停/割肉/活埋…）。<br>
      ④ 数据源：东方财富股吧「{STOCK_NAME}吧」移动端接口，已剔除资讯帖、公告及自媒体转载。<br>
      ⑤ 局限：词典法对长文/反讽有误判；早期周（2024-09 附近）发帖量可能受接口深翻页样本覆盖影响；情绪温度计不代表股价涨跌方向。
    </p>
  </div>

  <p class="disc"><b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。</p>
</div>

<script>
var weeks = {json.dumps(weeks)};
var panics = {json.dumps(panics)};
var totals = {json.dumps(totals)};
var bearRatios = {json.dumps(bear_ratios)};
var strengths = {json.dumps(strengths)};
var prices = {json.dumps(prices)};
var hasPrice = {str(has_price).lower()};

echarts.init(document.getElementById('panic')).setOption({{
  tooltip: {{ trigger:'axis', formatter:function(p){{ var s = p[0].name; var out = s; p.forEach(function(it){{ if(it.seriesName==='恐慌指数') out += '<br>恐慌指数: ' + it.value; if(it.seriesName==='股价') out += '<br>股价: ' + it.value; if(it.seriesName==='看空占比') out += '<br>看空占比: ' + it.value + '%'; }}); return out; }} }},
  grid: {{ left:60, right:110, top:30, bottom:50 }},
  xAxis: {{ type:'category', data:weeks, boundaryGap:false, axisLabel:{{ rotate:45, fontSize:10 }} }},
  yAxis: [
    {{ type:'value', min:0, name:'恐慌指数', position:'left' }},
    {{ type:'value', min:20, name:'股价(HK$)', position:'right' }},
    {{ type:'value', min:0, max:100, name:'看空占比%', position:'right', offset:55, splitLine:{{ show:false }} }}
  ],
  series: [{{
    name:'恐慌指数', type:'line', data:panics, smooth:true, yAxisIndex:0,
    lineStyle:{{ width:2, color:'#2b6de8' }}, itemStyle:{{ color:'#2b6de8' }},
    markLine:{{ data:[{{ yAxis:0, name:'多空分界 0' }},{{ yAxis:3000, name:'极度恐慌线' }},{{ yAxis:{_q80}, name:'高恐慌线' }},{{ yAxis:{_q50}, name:'中位线' }}], lineStyle:{{ type:'dashed', color:'#999' }} }}
  }},{{
    name:'股价', type:'line', data:prices, smooth:true, yAxisIndex:1,
    lineStyle:{{ width:2, color:'#e03a3a' }}, itemStyle:{{ color:'#e03a3a' }},
    areaStyle:{{ color:'rgba(224,58,58,0.05)' }}
  }},{{
    name:'看空占比', type:'line', data:bearRatios, smooth:true, yAxisIndex:2,
    lineStyle:{{ width:1.5, color:'#1a9e5c', type:'dashed' }}, itemStyle:{{ color:'#1a9e5c' }}
  }}]
}});

echarts.init(document.getElementById('ratio')).setOption({{
  tooltip:{{ trigger:'axis', formatter:function(p){{ return p[0].name + ': 看空占比 ' + p[0].value + '%'; }} }},
  grid:{{ left:40, right:20, top:30, bottom:50 }},
  xAxis:{{ type:'category', data:weeks, boundaryGap:false, axisLabel:{{ rotate:45, fontSize:10 }} }},
  yAxis:{{ type:'value', min:0, max:100, name:'看空占比(%)' }},
  series:[{{ type:'line', data:bearRatios, smooth:true, lineStyle:{{ color:'#1a9e5c', width:2 }}, itemStyle:{{ color:'#1a9e5c' }},
    markLine:{{ data:[{{ yAxis:50 }}], lineStyle:{{ type:'dashed', color:'#999' }}, label:{{ formatter:'多空平衡 50%' }} }} }}]
}});

echarts.init(document.getElementById('volume')).setOption({{
  tooltip:{{ trigger:'axis' }},
  grid:{{ left:50, right:20, top:30, bottom:50 }},
  xAxis:{{ type:'category', data:weeks, boundaryGap:true, axisLabel:{{ rotate:45, fontSize:10 }} }},
  yAxis:{{ type:'value', name:'发帖量' }},
  series:[{{ type:'bar', data:totals, itemStyle:{{ color:'#2b6de8' }} }}]
}});

echarts.init(document.getElementById('strength')).setOption({{
  tooltip:{{ trigger:'axis', formatter:function(p){{ return p[0].name + ': 情感 ' + p[0].value; }} }},
  grid:{{ left:40, right:20, top:30, bottom:50 }},
  xAxis:{{ type:'category', data:weeks, boundaryGap:false, axisLabel:{{ rotate:45, fontSize:10 }} }},
  yAxis:{{ type:'value', min:-1, max:1, name:'情感均值' }},
  series:[{{ type:'line', data:strengths, smooth:true, lineStyle:{{ color:'#e03a3a', width:2 }}, itemStyle:{{ color:'#e03a3a' }},
    markLine:{{ data:[{{ yAxis:0 }}], lineStyle:{{ type:'dashed', color:'#999' }}, label:{{ formatter:'中性 0' }} }} }}]
}});
</script>
</body>
</html>
"""

out = os.path.join(BASE, "output", OUT_HTML)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"100 周报告已生成: {out}")
print(f"周期 {weeks[0]} ~ {weeks[-1]}, 完整 {len(COMPLETE)} 周")
