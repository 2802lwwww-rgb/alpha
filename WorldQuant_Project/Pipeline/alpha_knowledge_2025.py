# 🧠 WorldQuant Brain Alpha 构造知识库 (2025-2026)
# 来源：WQB官方文档 + GitHub开源项目 + 量化研究论文 + IQC竞赛经验
# 更新时间：2026-04-30

## ═══════════════════════════════════════════
## 第一章：经济学含义 → 操作符映射
## ═══════════════════════════════════════════

### 1. 均值回归 (Mean Reversion)
# 经济学逻辑：价格偏离内在价值后会回归
# 适用场景：基本面数据（PE、PB、EV/EBITDA）
# 核心操作符：ts_zscore, ts_delta, rank
# 参数指南：
#   - 短期回归：lookback = 20-60天
#   - 长期回归：lookback = 120-252天
# 模板：
MEAN_REVERSION_TEMPLATES = [
    # 模板1：行业内Z-Score均值回归（最稳健）
    "ts_decay_linear(group_neutralize(-ts_zscore({field}, 63), subindustry), 40)",
    # 模板2：价格偏离度回归
    "ts_decay_linear(group_neutralize(rank(-ts_delta({field}, 20) / ts_std_dev({field}, 60)), subindustry), 30)",
    # 模板3：行业排名均值回归
    "ts_decay_linear(group_rank(-ts_zscore({field}, 126), industry), 60)",
]

### 2. 动量 (Momentum)
# 经济学逻辑：强者恒强，过去表现好的股票短期内继续表现好
# 适用场景：价格、成交量、分析师预期修正
# 核心操作符：ts_rank, ts_delta, ts_mean
# 参数指南：
#   - 短期动量：5-20天（高换手率风险）
#   - 中期动量：60-126天（最佳平衡点）
#   - 长期动量：252天（低换手，但信号弱）
# 模板：
MOMENTUM_TEMPLATES = [
    # 模板1：中期动量排名
    "ts_decay_linear(group_neutralize(ts_rank({field}, 126), subindustry), 40)",
    # 模板2：加速动量（一阶差分的差分）
    "ts_decay_linear(group_neutralize(ts_delta(ts_delta({field}, 60), 20), subindustry), 30)",
    # 模板3：相对强弱动量
    "ts_decay_linear(group_neutralize(rank({field} / ts_mean({field}, 252)), subindustry), 45)",
]

### 3. 分析师预期修正 (Analyst Revision)
# 经济学逻辑：分析师调高/调低预期时，市场反应滞后
# 适用场景：EPS预期、收入预期、目标价
# 核心操作符：ts_delta, ts_zscore, rank
# 关键：这是WQB上最容易出高分的方向之一
# 模板：
ANALYST_REVISION_TEMPLATES = [
    # 模板1：EPS预期变化（经典）
    "ts_decay_linear(group_neutralize(ts_delta(rank({field}), 20), subindustry), 30)",
    # 模板2：预期变化加速度
    "ts_decay_linear(group_neutralize(ts_zscore(ts_delta({field}, 20), 60), subindustry), 40)",
    # 模板3：预期共识偏离
    "ts_decay_linear(group_neutralize(rank({field}) - ts_mean(rank({field}), 60), subindustry), 35)",
]

### 4. 情绪因子 (Sentiment)
# 经济学逻辑：新闻情绪影响短期股价走势
# 适用场景：新闻数据、社交媒体数据
# 核心操作符：ts_decay_linear, ts_mean, group_neutralize
# 关键注意：情绪数据噪声大，必须做平滑和中性化
# 模板：
SENTIMENT_TEMPLATES = [
    # 模板1：情绪平滑（去噪）
    "ts_decay_linear(group_neutralize(ts_mean({field}, 5), subindustry), 20)",
    # 模板2：情绪偏离（相对行业）
    "ts_decay_linear(group_neutralize(rank({field}) - group_mean(rank({field}), subindustry), subindustry), 25)",
    # 模板3：情绪动量
    "ts_decay_linear(group_neutralize(ts_delta(ts_mean({field}, 5), 10), subindustry), 30)",
]

### 5. 基本面质量 (Fundamental Quality)
# 经济学逻辑：财务健康的公司长期跑赢
# 适用场景：ROE、现金流、负债率
# 核心操作符：rank, group_neutralize, ts_decay_linear
# 模板：
FUNDAMENTAL_QUALITY_TEMPLATES = [
    # 模板1：行业内财务质量排名
    "ts_decay_linear(group_neutralize(rank({field}), subindustry), 60)",
    # 模板2：市值分桶财务排名（消除大小盘偏差）
    "ts_decay_linear(group_neutralize(rank({field}), bucket(rank(cap), range='0.1,1,0.1')), 40)",
    # 模板3：财务趋势变化
    "ts_decay_linear(group_neutralize(ts_delta(rank({field}), 60), subindustry), 45)",
]

### 6. 跨数据集对冲 (Cross-Dataset Hedging)
# 经济学逻辑：当两个不同维度的信号同时确认时，信号更强
# 适用场景：基本面 × 情绪，分析师 × 价格
# 核心操作符：vector_neut, ts_corr
# 模板：
CROSS_DATASET_TEMPLATES = [
    # 模板1：向量对冲（基本面 vs 情绪）
    "ts_decay_linear(group_neutralize(vector_neut(rank({field1}), rank({field2})), subindustry), 45)",
    # 模板2：跨维度相关性
    "ts_decay_linear(group_neutralize(ts_corr(rank({field1}), rank({field2}), 60), subindustry), 40)",
    # 模板3：双信号乘积（非线性组合）
    "ts_decay_linear(group_neutralize(ts_zscore({field1}, 60) * ts_rank({field2}, 60), subindustry), 35)",
]

## ═══════════════════════════════════════════
## 第二章：参数调优指南
## ═══════════════════════════════════════════

PARAMETER_GUIDE = {
    "ts_decay_linear": {
        "作用": "线性衰减平滑，降低换手率",
        "参数d": {
            "20-30": "短期信号，换手率较高(>10%)，适合新闻/情绪",
            "40-60": "中期信号，换手率适中(3%-8%)，最佳平衡点",
            "80-120": "长期信号，换手率很低(<2%)，可能低于提交门槛"
        },
        "注意": "d太大会导致turnover<1%被平台拒绝"
    },
    "ts_zscore": {
        "作用": "标准化，测量偏离程度",
        "参数d": {
            "20": "短期异常检测",
            "63": "季度级别标准化（最常用）",
            "126": "半年级别",
            "252": "年度级别"
        }
    },
    "ts_rank": {
        "作用": "时间序列排名，捕捉动量",
        "参数d": {
            "20-60": "短中期动量",
            "126": "中期动量（推荐）",
            "252": "长期动量"
        }
    },
    "ts_corr": {
        "作用": "计算两个序列的相关性",
        "参数d": {
            "20": "短期相关性（噪声大）",
            "60": "中期相关性（推荐）",
            "120-252": "长期相关性（稳定但滞后）"
        }
    },
    "group_neutralize": {
        "作用": "消除分组效应（行业/板块偏差）",
        "分组选择": {
            "subindustry": "最细粒度，推荐用于基本面和情绪",
            "industry": "中等粒度，用于宏观趋势",
            "sector": "最粗粒度，用于大类资产配置",
            "bucket(rank(cap))": "市值分桶，消除大小盘偏差"
        }
    },
    "neutralization设置": {
        "SUBINDUSTRY": "推荐默认设置，最安全",
        "INDUSTRY": "适合宏观因子",
        "MARKET": "最激进，容易导致低Sharpe",
        "NONE": "不推荐，容易过拟合到市值或行业"
    }
}

## ═══════════════════════════════════════════
## 第三章：字段分类与最佳搭配
## ═══════════════════════════════════════════

FIELD_CATEGORY_STRATEGY = {
    "Fundamental（基本面）": {
        "代表字段": ["earnings_per_share", "book_value", "revenue", "net_income", "ebitda"],
        "最佳模板": "均值回归 + 基本面质量",
        "中性化": "subindustry（必须！基本面高度行业相关）",
        "decay": "40-60（基本面变化慢）"
    },
    "Analyst（分析师）": {
        "代表字段前缀": "anl4_",
        "最佳模板": "分析师预期修正",
        "中性化": "subindustry",
        "decay": "20-40（分析师修正有时效性）",
        "关键": "这是WQB上出高分概率最大的数据类"
    },
    "Sentiment（情绪）": {
        "代表字段前缀": ["snt1_", "nws12_", "nws18_"],
        "最佳模板": "情绪因子 + 跨数据集对冲",
        "中性化": "subindustry",
        "decay": "15-30（情绪衰减快）",
        "关键": "必须做5-10天均值平滑去噪"
    },
    "Price/Volume（价量）": {
        "代表字段": ["close", "open", "high", "low", "volume", "vwap", "returns"],
        "最佳模板": "动量",
        "中性化": "可选（价量信号行业依赖性低）",
        "decay": "30-60",
        "关键": "价量因子竞争激烈，很难出新的高分"
    },
    "Model（模型）": {
        "代表字段前缀": "mdl77_, mdl177_",
        "最佳模板": "基本面质量 + 均值回归",
        "中性化": "subindustry",
        "decay": "40-60",
        "注意": "部分模型字段计算量大，可能TIMEOUT"
    }
}

## ═══════════════════════════════════════════
## 第四章：致命错误清单（从我们的失败中学到的）
## ═══════════════════════════════════════════

FATAL_MISTAKES = [
    "1. 把分类字段（sector, industry, subindustry）当因子用 → SIM ERROR",
    "2. ts_regression不加rettype参数 → Unknown Platform Error",
    "3. 用过于复杂的嵌套公式 → TIMEOUT",
    "4. decay设太大导致turnover<1% → 平台拒绝提交",
    "5. 不做group_neutralize直接rank → 捕捉到的是市值效应而非alpha",
    "6. 重复提交已回测过的公式 → 浪费API配额",
    "7. 情绪数据不做平滑直接用 → 噪声太大，Sharpe极低",
    "8. 用VECTOR类型字段不先做vec_avg → 维度不匹配报错",
]

## ═══════════════════════════════════════════
## 第五章：Fitness公式（核心评价标准）
## ═══════════════════════════════════════════

# Fitness = sqrt(|Returns| / max(Turnover, 0.125)) × Sharpe
# 要最大化Fitness，需要同时：
#   1. 高Sharpe（>1.25 才能提交）
#   2. 高Returns（绝对收益越高越好）
#   3. 低Turnover（但不能低于1%，否则提交被拒）
# 最佳Turnover区间：3% - 15%
