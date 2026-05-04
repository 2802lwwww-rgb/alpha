import pandas as pd
import os

def clean_results():
    results_path = 'sprint_results_v5.csv'
    if os.path.exists(results_path):
        try:
            df = pd.read_csv(results_path)
            # 只保留 Sharpe > 0 的行
            df_clean = df[df['sharpe'] > 0]
            df_clean.to_csv(results_path, index=False)
            print(f"Cleaned {results_path}: removed {len(df) - len(df_clean)} negative factors.")
        except Exception as e:
            print(f"Error cleaning {results_path}: {e}")

if __name__ == "__main__":
    clean_results()
