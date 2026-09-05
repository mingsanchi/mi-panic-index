# -*- coding: utf-8 -*-
"""
生成恐慌指数 HTML 可视化报告
读取 data/result.json，生成 output/panic_report.html
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "data", "result.json"), encoding="utf-8") as f:
    R = json.load(f)

P = R["panic_index"]
DAILY = R["daily"]

# 时序数据：仅保留样本量充足的天（total>=20），避免小样本噪声
recent = [d for d in DAILY if d["total"] >= 20]
dates = [d["date"][5:] for d in recent]  # MM-DD
totals = [d["total"] for d in recent]
bulls = [d["bull"] for d in recent]
bears = [d["bear"] for d in recent]
bear_ratios = [round(d["bear_ratio"] * 100, 1) for d in recent]

# 三因子贡献
br_c = round(P["bear_ratio"] * 0.45 * 100, 1)
se_c = round(P["sentiment"] * 0.40 * 100, 1)
vo_c = round(P["volume_factor"] * 0.15 * 100, 1)

# 典型帖子（来自真实抓取数据，人工筛选明确样本）
BEAR_SAMPLES = [
    ("尾盘太诡异了！明天活埋，起码大跌8个点", 102, 4),
    ("明天晚上发财报，今天明天最后的逃跑机会，后天起码-5%起步", 72, 3),
    ("今天的走势预示着财报不给力明天要大跌，已被深套走不了了", 93, 4),
    ("不管明天财报好坏都会大跌，这是惯例", 36, 1),
    ("明天跌10-15%，明天雷子做米粉们真爹了", 137, 5),
    ("垃圾韭菜股，快清仓", 16, 0),
]
BULL_SAMPLES = [
    ("市盈率这么低，闭眼进，长期看好，未来2-3年会成为百元股票", 145, 9),
    ("还是看好你，一股不卖", 102, 1),
    ("里程碑时刻！SU7交付破50万台，小米汽车驶入黄金爆发期，历史性突破可喜可贺", 94, 1),
    ("小米已经很接近回撤0.382了，调整很快结束，要买进了", 101, 6),
    ("逐步买回", 86, 5),
    ("第一，公司回购，公司知道营业状况，认为价格低于价值太远，肯定选择回购", 106, 5),
]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小米集团-W 恐慌指数报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  :root {{
    --bg: #f7f8fa; --card: #ffffff; --text: #1f2329; --sub: #646a73;
    --line: #e5e6eb; --red: #e03a3a; --green: #1a9e5c; --accent: #2b6de8;
    --amber: #d97706;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.6; }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 24px 20px 60px; }}
  h1 {{ font-size: 24px; font-weight: 700; }}
  .sub {{ color: var(--sub); font-size: 13px; margin-top: 4px; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 20px 24px; margin-top: 16px; }}
  .card h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; }}
  /* 首屏结论 */
  .hero {{ display: flex; gap: 24px; align-items: stretch; flex-wrap: wrap; }}
  .gauge-box {{ flex: 1 1 340px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 24px; text-align: center; }}
  .gauge-val {{ font-size: 64px; font-weight: 800; line-height: 1; }}
  .gauge-label {{ font-size: 16px; font-weight: 600; margin-top: 8px; }}
  .gauge-desc {{ color: var(--sub); font-size: 12px; margin-top: 6px; }}
  .conclusion {{ flex: 1 1 340px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 24px; display: flex; flex-direction: column; justify-content: center; }}
  .conclusion h3 {{ font-size: 15px; font-weight: 600; margin-bottom: 8px; }}
  .conclusion ul {{ list-style: none; }}
  .conclusion li {{ font-size: 13px; color: var(--text); padding: 6px 0; border-bottom: 1px dashed var(--line); }}
  .conclusion li:last-child {{ border-bottom: none; }}
  .conclusion b {{ color: var(--red); }}
  /* 因子卡片 */
  .factors {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
  .factor {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px; }}
  .factor .name {{ font-size: 13px; color: var(--sub); }}
  .factor .val {{ font-size: 28px; font-weight: 700; margin: 6px 0; }}
  .factor .bar {{ height: 6px; background: #eef0f3; border-radius: 3px; overflow: hidden; margin-top: 8px; }}
  .factor .bar i {{ display: block; height: 100%; background: var(--accent); }}
  .factor .note {{ font-size: 11px; color: var(--sub); margin-top: 6px; }}
  /* 图表 */
  .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .chart-box {{ height: 340px; }}
  .chart-full {{ height: 340px; }}
  @media (max-width: 760px) {{ .charts, .factors {{ grid-template-columns: 1fr; }} }}
  /* 表格 */
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); }}
  th {{ color: var(--sub); font-weight: 500; background: #fafbfc; }}
  .tag {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; }}
  .tag-bear {{ background: #fdeaea; color: var(--green); }}
  .tag-bull {{ background: #fceaea; color: var(--red); }}
  .tag-neutral {{ background: #eef0f3; color: var(--sub); }}
  /* 方法论 */
  .formula {{ background: #f6f8fb; border-radius: 8px; padding: 14px 16px; font-family: "SF Mono", Menlo, monospace; font-size: 13px; margin: 10px 0; }}
  .src {{ font-size: 12px; color: var(--sub); }}
  .disc {{ font-size: 12px; color: var(--sub); border-top: 1px solid var(--line); margin-top: 20px; padding-top: 14px; }}
  .warn {{ color: var(--amber); font-weight: 600; }}
</style>
</head>
<body>
<div class="wrap">

  <h1>小米集团-W 散户恐慌指数</h1>
  <div class="sub">标的：小米集团-W（01810.HK）｜数据源：东方财富股吧 + 雪球｜统计时点：2026-08-17 16:22（盘中）｜样本：{P['total']} 条用户帖</div>

  <!-- 首屏结论 -->
  <div class="hero">
    <div class="gauge-box">
      <div class="gauge-val" style="color:var(--green);">{P['panic_index']}</div>
      <div class="gauge-label" style="color:var(--green);">{P['level']}</div>
      <div class="gauge-desc">恐慌指数 0-100，越高代表散户越恐慌</div>
    </div>
    <div class="conclusion">
      <h3>核心结论</h3>
      <ul>
        <li>散户情绪进入 <b>{P['level']}</b> 区间，恐慌指数 <b>{P['panic_index']}</b></li>
        <li>看空/看多比 <b>{round(P['bear_ratio']*100,1)}%</b>：有明确方向的帖子中，看空占比过半</li>
        <li>发帖量 <b>{P['today_posts']}</b> 条，为前 3 日均值的 <b>{round(P['today_posts']/max(P['baseline_posts'],1),1)}</b> 倍，财报前讨论显著放量</li>
        <li>驱动：<b>Q2 财报前夕</b> + 技术面下行 + 看空情绪蔓延</li>
      </ul>
    </div>
  </div>

  <!-- 三因子 -->
  <div class="factors">
    <div class="factor">
      <div class="name">看空/看多比（权重 45%）</div>
      <div class="val" style="color:var(--green);">{round(P['bear_ratio']*100,1)}%</div>
      <div class="bar"><i style="width:{round(P['bear_ratio']*100,1)}%;background:var(--green);"></i></div>
      <div class="note">看空 {P['bear']} 帖 vs 看多 {P['bull']} 帖（另有 {P['neutral']} 帖中性）</div>
    </div>
    <div class="factor">
      <div class="name">情感指数（权重 40%）</div>
      <div class="val" style="color:var(--amber);">{round(P['sentiment']*100,1)}</div>
      <div class="bar"><i style="width:{round(P['sentiment']*100,1)}%;background:var(--amber);"></i></div>
      <div class="note">按热度加权的情感均值 {P['mean_strength']}（-1 全看空 ~ +1 全看多）</div>
    </div>
    <div class="factor">
      <div class="name">发帖量指数（权重 15%）</div>
      <div class="val" style="color:var(--accent);">{round(P['volume_factor']*100,0)}</div>
      <div class="bar"><i style="width:{round(P['volume_factor']*100,0)}%;"></i></div>
      <div class="note">今日 {P['today_posts']} 条 / 基线 {round(P['baseline_posts'],0)} 条（2 倍封顶）</div>
    </div>
  </div>

  <!-- 图表 -->
  <div class="card">
    <h2>情感分布与发帖量时序</h2>
    <div class="charts">
      <div id="pie" class="chart-box"></div>
      <div id="bar" class="chart-box"></div>
    </div>
  </div>

  <div class="card">
    <h2>看空占比趋势（近 7 日）</h2>
    <div id="line" class="chart-full"></div>
  </div>

  <!-- 典型帖子 -->
  <div class="card">
    <h2>代表性帖子（看空 vs 看多）</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
      <div>
        <h3 style="font-size:14px;color:var(--green);margin-bottom:8px;">看空派（{P['bear']} 帖）</h3>
        <table>
          <tr><th>帖子</th><th>阅读</th></tr>
          {"".join(f"<tr><td>{esc(t)}</td><td>{r}</td></tr>" for t,r,_ in BEAR_SAMPLES)}
        </table>
      </div>
      <div>
        <h3 style="font-size:14px;color:var(--red);margin-bottom:8px;">看多派（{P['bull']} 帖）</h3>
        <table>
          <tr><th>帖子</th><th>阅读</th></tr>
          {"".join(f"<tr><td>{esc(t)}</td><td>{r}</td></tr>" for t,r,_ in BULL_SAMPLES)}
        </table>
      </div>
    </div>
  </div>

  <!-- 方法论 -->
  <div class="card">
    <h2>指数构建方法论</h2>
    <p style="font-size:13px;">恐慌指数由三个维度加权合成，全部基于真实抓取的散户帖子数据：</p>
    <div class="formula">Panic = 100 × ( 0.45×看空比 + 0.40×情感指数 + 0.15×发帖量指数 )</div>
    <table>
      <tr><th>因子</th><th>定义</th><th>本次贡献</th></tr>
      <tr><td>看空/看多比</td><td>看空帖 /（看空帖+看多帖），衡量方向明确帖子中的空头占比</td><td>{br_c} 分</td></tr>
      <tr><td>情感指数</td><td>(1 - 热度加权情感均值)/2，热度=阅读量+评论量，让高热度帖权重更大</td><td>{se_c} 分</td></tr>
      <tr><td>发帖量指数</td><td>今日发帖量 / 前3日均值（2倍封顶），恐慌时散户发帖激增</td><td>{vo_c} 分</td></tr>
    </table>
    <p style="font-size:12px;color:var(--sub);margin-top:10px;">
      NLP 方案：金融看多/看空词典法（主）+ SnowNLP 连续情感分（参考）。词典法对标题+正文匹配看多词（涨停/抄底/利好…）与看空词（跌停/割肉/活埋…），含否定词处理；标题权重高于正文。
    </p>
  </div>

  <!-- 数据来源 -->
  <div class="card">
    <h2>数据来源与说明</h2>
    <p class="src">
      ① 东方财富股吧「小米集团-W吧」：经移动端接口抓取 {P['total']-5} 条用户帖（含标题、正文、阅读量、评论量、发布时间），已剔除资讯帖、公告及自媒体转载。<br>
      ② 雪球「小米集团-W(01810)」：抓取 5 条当日讨论帖（含技术面观点与深度长文）。<br>
      ③ 帖子时间跨度：2026-08-13 至 2026-08-17，以当日（08-17）为主。<br>
      ④ 统计时点：2026-08-17 16:22（盘中），当日发帖量仍将随时间增长。
    </p>
    <p class="src" style="margin-top:8px;">
      <span class="warn">局限说明：</span>① 股吧样本以散户为主，存在情绪极端化、水军与重复发帖噪声；② 词典法对长文、反讽的识别存在误差；③ 发帖量基线仅取最近 3 个完整日，样本周期有限；④ 恐慌指数为情绪温度计，<b>不代表股价涨跌方向</b>。
    </p>
  </div>

  <p class="disc">
    <b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。
  </p>
</div>

<script>
var dates = {json.dumps(dates)};
var totals = {json.dumps(totals)};
var bulls = {json.dumps(bulls)};
var bears = {json.dumps(bears)};
var bearRatios = {json.dumps(bear_ratios)};

// 情感分布饼图
echarts.init(document.getElementById('pie')).setOption({{
  tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}} 帖 ({{d}}%)' }},
  legend: {{ bottom: 0 }},
  series: [{{
    type: 'pie', radius: ['40%', '68%'], center: ['50%', '45%'],
    label: {{ formatter: '{{b}}\\n{{c}} 帖' }},
    data: [
      {{ name: '看空', value: {P['bear']}, itemStyle: {{ color: '#1a9e5c' }} }},
      {{ name: '看多', value: {P['bull']}, itemStyle: {{ color: '#e03a3a' }} }},
      {{ name: '中性', value: {P['neutral']}, itemStyle: {{ color: '#b8bcc4' }} }}
    ]
  }}]
}});

// 发帖量时序柱状图
echarts.init(document.getElementById('bar')).setOption({{
  tooltip: {{ trigger: 'axis' }},
  legend: {{ data: ['看多', '看空'], bottom: 0 }},
  xAxis: {{ type: 'category', data: dates }},
  yAxis: {{ type: 'value', name: '帖数' }},
  series: [
    {{ name: '看多', type: 'bar', stack: 't', data: bulls, itemStyle: {{ color: '#e03a3a' }} }},
    {{ name: '看空', type: 'bar', stack: 't', data: bears, itemStyle: {{ color: '#1a9e5c' }} }}
  ]
}});

// 看空占比趋势折线
echarts.init(document.getElementById('line')).setOption({{
  tooltip: {{ trigger: 'axis', formatter: function(p){{ return p[0].name + ': 看空占比 ' + p[0].value + '%'; }} }},
  xAxis: {{ type: 'category', data: dates, boundaryGap: false }},
  yAxis: {{ type: 'value', min: 0, max: 100, name: '看空占比(%)' }},
  series: [{{
    type: 'line', data: bearRatios, smooth: true,
    lineStyle: {{ color: '#1a9e5c', width: 3 }},
    itemStyle: {{ color: '#1a9e5c' }},
    areaStyle: {{ color: 'rgba(26,158,92,0.12)' }},
    markLine: {{ data: [{{ yAxis: 50 }}], lineStyle: {{ type: 'dashed', color: '#999' }}, label: {{ formatter: '多空平衡线 50%' }} }}
  }}]
}});
</script>
</body>
</html>
"""

out_path = os.path.join(BASE, "output", "panic_report.html")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"报告已生成: {out_path}")
print(f"恐慌指数: {P['panic_index']} ({P['level']}) | 样本 {P['total']} 条")
