import pandas as pd
import os

def extract_candidates():
    # 支持新旧两种数据源
    input_files = ['../sprint_results_v6.csv', '../sprint_results_v5.csv', '../sprint_failed.csv']
    output_file = './optimization_targets.csv'
    
    print(f"--- 05_Candidate_Extractor V2: Identifying Diamonds in the Rough ---")
    
    all_dfs = []
    for f in input_files:
        if os.path.exists(f):
            try:
                # 针对 V6 无表头格式进行兼容
                if 'v6' in f or 'results' in f:
                    df = pd.read_csv(f, names=['expression', 'sharpe', 'fitness', 'turnover', 'sub_s', 'sc', 'category'])
                else:
                    df = pd.read_csv(f)
                all_dfs.append(df)
                print(f"  Loaded {len(df)} rows from {f}")
            except: pass
    
    if not all_dfs:
        print("Error: No input files found.")
        return
    
    df = pd.concat(all_dfs, ignore_index=True)
    
    # 转换数值列（兼容新旧格式）
    for col in ['sharpe', 'turnover', 'fitness', 'sc']:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 过滤泡沫因子（|Sharpe|>4 且 Turnover>=90% = 过拟合垃圾）
    bubble_mask = (df['sharpe'].abs() > 3.0) & (df['turnover'] >= 0.9)
    df = df[~bubble_mask]
    
    import math
    # 定义提取规则（V6 严选版：加入动态子池夏普门槛）
    # 动态门槛 = 0.75 * sqrt(1000/3000) * abs(s)
    def check_sub_s(row):
        dynamic_thresh = 0.75 * math.sqrt(1000/3000) * abs(row['sharpe'])
        return abs(row['sub_s']) >= dynamic_thresh

    mask = (df['sharpe'].abs() > 0.9) & (df['fitness'].abs() > 0.7) & (df['turnover'] < 0.8)
    candidates = df[mask].copy()
    
    # 进一步应用子池过滤
    if 'sub_s' in candidates.columns:
        candidates['sub_s'] = pd.to_numeric(candidates['sub_s'], errors='coerce').fillna(0)
        candidates = candidates[candidates.apply(check_sub_s, axis=1)]
    
    # --- 自动归一化逻辑：将负夏普因子翻转为正向 ---
    def normalize_alpha(row):
        if row['sharpe'] < 0:
            row['expression'] = f"-1 * ({row['expression']})"
            row['sharpe'] = -row['sharpe']
            row['fitness'] = -row['fitness']
        return row
    
    candidates = candidates.apply(normalize_alpha, axis=1)
    
    # 去重（此时 A 和 -1*A 已经变成了相同的字符串）
    candidates = candidates.drop_duplicates(subset=['expression'])

    # 添加优化方向建议
    def get_suggestion(row):
        # 此时 sharpe 已经全是正数了
        if row['sc'] > 0.7:
            return "SC_HIGH: Orthogonalize or change denominator"
        if row['turnover'] > 0.7:
            return "TURNOVER_HIGH: Increase decay from 40 to 60"
        if row['turnover'] < 0.01:
            return "TURNOVER_LOW: Decrease decay from 60 to 30"
        if row['sharpe'] < 1.25:
            return "BOOST: Try Cap-Bucketed neutralization"
        return "GENERAL: Refine parameters"

    candidates['suggestion'] = candidates.apply(get_suggestion, axis=1)
    
    # 按潜力排序（绝对值越高越优先）
    candidates['abs_sharpe'] = candidates['sharpe'].abs()
    candidates = candidates.sort_values('abs_sharpe', ascending=False)
    candidates = candidates.drop(columns=['abs_sharpe'])
    # 追加模式：去重并追加
    if os.path.exists(output_file):
        try:
            # 忽略手动添加的无意义行（如"第一轮"），提取已有因子
            existing_df = pd.read_csv(output_file, on_bad_lines='skip', engine='python')
            if 'expression' in existing_df.columns:
                existing_exprs = set(existing_df['expression'].dropna().unique())
                candidates = candidates[~candidates['expression'].isin(existing_exprs)]
        except Exception as e:
            print(f"Warning: Could not parse existing output file for deduplication. {e}")
            
    if not candidates.empty:
        write_header = not os.path.exists(output_file) or os.path.getsize(output_file) == 0
        # 强制只输出指定的列，避免 Pandas 产生多余列
        out_cols = ['expression', 'sharpe', 'fitness', 'turnover', 'sub_s', 'sc', 'category', 'suggestion']
        candidates_out = candidates[[c for c in out_cols if c in candidates.columns]]
        candidates_out.to_csv(output_file, mode='a', header=write_header, index=False)
        print(f"\nSuccess! Appended {len(candidates)} NEW high-potential candidates to {output_file}")
    else:
        print(f"\nAll high-potential candidates are already in {output_file}. Nothing new to append.")
    print("\n--- Top Optimization Targets ---")
    cols = [c for c in ['expression', 'sharpe', 'turnover', 'sub_s', 'fitness', 'sc', 'suggestion'] if c in candidates.columns]
    print(candidates[cols].head(10).to_string())

if __name__ == "__main__":
    extract_candidates()
