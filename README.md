# 小米集团-W 散户恐慌指数

基于**东方财富股吧**散户帖文的量化情绪分析工具，面向港股与 A 股散户，构建自定义「恐慌/情绪指数」。

- 主标的：小米集团-W（01810.HK）
- A 股对照：永辉超市（601933.SH）

## 恐慌指数公式

```
Panic = 看空帖数 × (0.2 − 情感均值) / 0.2
```

- **情感均值** = 热度加权单帖看多/看空强度（范围 −1 ~ +1），权重 `w = 1 + √(阅读 + 2×评论)`
- **看空帖数** = 该周/该日词典法判定为「看空」的帖子数
- `Panic > 3000` 判定为「极度恐慌」，其余按历史分位数分档（高恐慌 / 恐慌 / 中性偏谨慎 / 温和）
- 负值表示乐观（看空帖少或整体看多）

## 情感分析

金融看多/看空词典法（纯规则），对标题 + 正文匹配：

- 看多词：涨停 / 抄底 / 利好 / 起飞 …
- 看空词：跌停 / 割肉 / 活埋 / 暴雷 …

已对「雷军」等实体词做误判修复（移除单字「雷」）。

## 目录结构

```
├── index.html                  # GitHub Pages 门户页
├── output/                     # 生成的 HTML 报告
│   ├── weekly_panic_report.html   # 100 周回顾（主报告）
│   ├── mi_90days_report.html      # 90 天
│   ├── mi_60days_report.html      # 60 天
│   └── ...
├── data/                       # 原始帖库 + 聚合结果
│   ├── eastmoney_history.jsonl    # 小米全量历史帖（~28 万条）
│   ├── weekly_panic.json          # 100 周周频指数
│   └── ...
├── scraper/                    # 抓取脚本
│   ├── eastmoney_history_scraper.py
│   └── incremental_update.py      # 增量更新
├── nlp/sentiment.py            # 词典法情感分析
├── weekly_analysis.py          # 周频聚合
├── weekly_report.py            # 100 周报告生成
├── daily_analysis.py           # 日频聚合
├── daily_report.py             # 日频报告生成
├── fetch_price.py              # 日线股价对齐
├── fetch_weekly_price.py       # 周线股价对齐
└── web_app.py                  # 交互式 Web 查询（FastAPI）
```

## 更新报告

```bash
# 1. 增量抓取新帖（截止日期之后）
python3 scraper/incremental_update.py hk01810 <起始日期> eastmoney_history.jsonl 100

# 2. 重算周频指数
python3 weekly_analysis.py eastmoney_history.jsonl weekly_panic.json

# 3. 刷新周线股价
python3 fetch_weekly_price.py 116.01810 20240101 <截止日期> mi_panic_price_aligned.json

# 4. 生成报告
python3 weekly_report.py "小米集团-W" "01810.HK" weekly_panic.json weekly_panic_report.html mi_panic_price_aligned.json
```

> 注意：`weekly_report.py` / `daily_report.py` 内含反斜杠 f-string，需使用 Python 3.12+ 运行（Python 3.9 会报语法错误）。

## GitHub Pages 部署

仓库以 `main` 分支根目录作为 Pages 源，`index.html` 为门户页。推送后：

**Settings → Pages → Build and deployment → Branch → main / (root)** → Save

页面地址：`https://<你的用户名>.github.io/<仓库名>/`

## 免责声明

以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。过往表现不预示未来收益。
