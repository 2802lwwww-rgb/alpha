import pandas as pd
import os

def analyze_performance():
    results_path = 'sprint_results_v5.csv'
    golden_path = 'golden_alphas_v5.csv'
    
    # 加载结果
    all_results = []
    if os.path.exists(results_path):
        all_results.append(pd.read_csv(results_path))
    if os.path.exists(golden_path):
        all_results.append(pd.read_csv(golden_path))
    
    if not all_results:
        print("No results found.")
        return
    
    df = pd.concat(all_results, ignore_index=True)
    
    # 定义“优质因子”标准
    # 注意：golden_alphas_v5.csv 里的因子已经符合标准，但我们也需要从总数里算比例
    df['is_golden'] = (abs(df['sharpe']) >= 1.25) & (abs(df['fitness']) >= 1.0) & (df['turnover'] <= 0.7)
    
    # 按模板统计
    stats = df.groupby('template').agg(
        total_attempts=('template', 'count'),
        golden_count=('is_golden', 'sum')
    )
    
    stats['success_rate'] = (stats['golden_count'] / stats['total_attempts'] * 100).round(2)
    stats = stats.sort_values(by='success_rate', ascending=False)
    
    print(stats.to_string())

if __name__ == "__main__":
    analyze_performance()
