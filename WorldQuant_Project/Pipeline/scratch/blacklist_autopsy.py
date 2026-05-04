import csv
import json
import os
from collections import Counter

def perform_autopsy():
    failed_file = 'sprint_failed.csv'
    blacklist_file = 'dynamic_blacklist.json'
    
    if not os.path.exists(failed_file):
        print(f"Error: {failed_file} not found.")
        return

    fields = []
    print(f"Analyzing {failed_file} for problematic fields...")
    
    with open(failed_file, 'r', encoding='utf-8') as f:
        # 尝试检测是否有表头
        sample = f.read(1024)
        f.seek(0)
        has_header = csv.Sniffer().has_header(sample)
        reader = csv.reader(f)
        if has_header: next(reader)
        
        for row in reader:
            if not row: continue
            expr = row[0]
            # 简单粗暴提取字段名：假设字段名都带下划线且是字母数字
            import re
            found = re.findall(r'[a-zA-Z0-9]+_[a-zA-Z0-9_]+', expr)
            fields.extend(found)

    # 统计前缀（取前两个下划线段，如 anl4_ads1）
    def get_prefix(f):
        parts = f.split('_')
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"
        return f

    prefixes = Counter([get_prefix(f) for f in fields])
    
    # 定义受保护的算子，严禁拉黑
    operators = {'ts_decay', 'group_neutralize', 'ts_delta', 'ts_std', 'ts_rank', 'ts_sum', 'ts_mean', 'ts_max', 'ts_min'}
    
    # 找出报错次数超过 3 次的前缀，且不在算子白名单内
    kill_list = [p for p, count in prefixes.items() if count >= 3 and p not in operators]
    print(f"Detected problematic prefixes: {kill_list}")

    # 加载现有黑名单并合并
    current_blacklist = []
    if os.path.exists(blacklist_file):
        with open(blacklist_file, 'r') as f:
            current_blacklist = json.load(f)
    
    # 合并去重
    new_blacklist = sorted(list(set(current_blacklist + kill_list)))
    
    with open(blacklist_file, 'w') as f:
        json.dump(new_blacklist, f, indent=4)
    
    print(f"Success! Blacklist updated. Total entries: {len(new_blacklist)}")
    print(f"Added new culprits: {set(kill_list) - set(current_blacklist)}")

if __name__ == "__main__":
    perform_autopsy()
