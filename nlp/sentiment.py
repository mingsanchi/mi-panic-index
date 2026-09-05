# -*- coding: utf-8 -*-
"""
中文股吧情感分析模块
方案：金融看多/看空词典法（主）+ SnowNLP 连续情感分（辅）
输出：每个帖子 -> {sentiment: 看多/看空/中性, bull_bear_score, snownlp_score}
"""
import re

# ============ 金融情感词典 ============
BULL_WORDS = [
    "涨停", "大涨", "暴涨", "拉升", "冲高", "起飞", "翻红", "新高", "突破",
    "反弹", "牛市", "利好", "抄底", "加仓", "满仓", "买入", "买点", "上车",
    "看好", "看多", "起飞", "腾飞", "暴拉", "主升", "翻倍", "赚钱", "盈利",
    "回购", "增持", "业绩", "超预期", "强势", "走强", "企稳", "止跌", "回升",
    "稳了", "别慌", "拿住", "持有", "长线", "价值", "低估", "香", "冲", "飞",
    "红盘", "上涨", "涨了", "要涨", "会涨", "还能涨", "向上", "买入机会",
    "逢低", "布局", "建仓", "仓位", "梭哈", "all in", "ALL IN", "干它", "搞起",
]
BEAR_WORDS = [
    "跌停", "大跌", "暴跌", "跳水", "崩盘", "崩了", "破位", "新低", "套牢",
    "割肉", "清仓", "减仓", "卖出", "卖点", "利空", "看空", "空头", "做空",
    "活埋", "砸盘", "跑路", "快跑", "撤退", "退市", "完蛋", "亏", "亏钱",
    "亏损", "腰斩", "下杀", "杀跌", "绿盘", "下跌", "跌了", "要跌", "还会跌",
    "向下", "危险", "风险", "恐慌", "慌", "怕", "暴雷", "爆雷", "爆仓", "止损",
    "割", "凉", "凉凉", "废了", "接盘", "站岗", "高位", "出货", "诱多",
    "套牢", "套住", "被套", "又套", "套一批", "深套", "闷杀", "阴跌", "缩水",
]

NEGATION_WORDS = ["不", "没", "别", "未", "无", "非", "否"]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\$[^$]*\$", " ", text)  # 去掉 $股票代码$
    text = re.sub(r"\[[^\]]*\]", " ", text)  # 去掉 [表情] 类
    text = re.sub(r"http\S+", " ", text)
    return text


def classify_by_dict(text: str):
    """词典法分类：返回 (bull_hits, bear_hits, 分类)"""
    text = clean_text(text)
    if not text:
        return 0, 0, "中性"

    bull = sum(1 for w in BULL_WORDS if w in text)
    bear = sum(1 for w in BEAR_WORDS if w in text)

    # 简单否定处理：如"不涨""别抄底"
    for neg in NEGATION_WORDS:
        for w in ["涨", "买", "抄底", "加仓", "利好", "看好"]:
            if neg + w in text:
                bull -= 1
                bear += 1
        for w in ["跌", "卖", "清仓", "割肉", "慌", "跑"]:
            if neg + w in text:
                bear -= 1
                bull += 1

    # 保证计数非负（否定处理可能使计数变负）
    bull = max(0, bull)
    bear = max(0, bear)

    if bull > bear:
        label = "看多"
    elif bear > bull:
        label = "看空"
    else:
        label = "中性"
    return bull, bear, label


def sentiment_score(text: str) -> dict:
    """综合情感分析，返回结构化结果"""
    bull, bear, label = classify_by_dict(text)
    # 看多/看空强度得分：[-1, 1]，词典命中差归一化
    if bull + bear > 0:
        strength = (bull - bear) / (bull + bear)
    else:
        strength = 0.0
    # 限制在 [-1, 1]
    strength = max(-1.0, min(1.0, strength))

    return {
        "label": label,           # 看多/看空/中性
        "bull_hits": bull,
        "bear_hits": bear,
        "strength": round(strength, 3),  # -1(强看空) ~ 1(强看多)
    }


def snownlp_score(text: str):
    """SnowNLP 连续情感分（0~1，>0.5 偏正面），作为辅助参考"""
    try:
        from snownlp import SnowNLP
        s = SnowNLP(clean_text(text))
        return round(s.sentiments, 3)
    except Exception:
        return 0.5


def analyze_post(post: dict) -> dict:
    """对单条帖子做完整情感分析（标题权重高于正文）"""
    title = post.get("title", "")
    content = post.get("content", "")
    # 标题情感权重更高（股吧标题往往就是核心情绪）
    t = sentiment_score(title)
    c = sentiment_score(content)
    full = sentiment_score(title + " " + content)

    # 综合标签：标题若明确看多看空则优先，否则用全文
    if t["label"] != "中性":
        label = t["label"]
    else:
        label = full["label"]

    sn = snownlp_score(title + " " + content)

    return {
        "postid": post.get("postid", ""),
        "title": title,
        "content": content,
        "label": label,
        "strength": full["strength"],
        "title_label": t["label"],
        "bull_hits": full["bull_hits"],
        "bear_hits": full["bear_hits"],
        "snownlp": sn,
        "read": post.get("read", 0),
        "reply": post.get("reply", 0),
        "update": post.get("update", "") or post.get("publish_time", ""),
        "author": post.get("author", ""),
    }


if __name__ == "__main__":
    samples = [
        "尾盘太诡异了！明天活埋，起码大跌8个点",
        "小米汽车SU7交付突破50万台，长期看好，逢低布局",
        "早上6.6个点，呜呜呜",
        "要涨了",
        "又套一批？",
        "小米机器人第二增长曲线已落地，价值低估",
        "砸盘是为了让你割肉",
    ]
    for s in samples:
        r = sentiment_score(s)
        print(f"{r['label']:>3} | strength={r['strength']:+.2f} | {s}")
