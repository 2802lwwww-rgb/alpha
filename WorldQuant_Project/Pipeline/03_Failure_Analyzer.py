import pandas as pd
import re
import json

def analyze_failures():
    import os
    print("--- 03_Failure_Analyzer: Multi-Source Failure Analysis ---")
    
    failure_data = []

    # Source 1: sprint_failed.csv (Structured data)
    if os.path.exists('sprint_failed.csv'):
        try:
            df_csv = pd.read_csv('sprint_failed.csv')
            for _, row in df_csv.iterrows():
                failure_data.append({
                    'message': str(row.get('message', '')),
                    'expression': str(row.get('expression', '')),
                    'sharpe': row.get('sharpe', 0)
                })
            print(f"Loaded {len(df_csv)} failures from sprint_failed.csv")
        except Exception as e:
            print(f"Warning: Error reading sprint_failed.csv: {e}")

    # Source 2: sprint_miner_v5.log (Unstructured data)
    if os.path.exists('sprint_miner_v5.log'):
        try:
            with open('sprint_miner_v5.log', 'r', encoding='utf-8') as f:
                log_content = f.read()
            # Regex to match: SIM ERROR: <msg> | Expr: <expr>
            log_matches = re.findall(r'SIM ERROR: (.*?) \| Expr: (.*?)$', log_content, re.MULTILINE)
            for msg, expr in log_matches:
                failure_data.append({
                    'message': msg.strip(),
                    'expression': expr.strip(),
                    'sharpe': 0
                })
            print(f"Extracted {len(log_matches)} potential failures from sprint_miner_v5.log")
        except Exception as e:
            print(f"Warning: Error reading sprint_miner_v5.log: {e}")

    if not failure_data:
        print("No failure data found in CSV or Logs.")
        return

    unknown_vars = set()
    event_vars = set()
    incompatible_units = set()
    zero_sharpe_fields = set()

    # Pattern to extract field names from expressions
    field_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
    operators = {'ts_decay_linear', 'group_neutralize', 'ts_zscore', 'ts_regression', 
                 'rank', 'subindustry', 'returns', 'vec_avg', 'ts_rank', 'ts_delta', 
                 'ts_mean', 'ts_std_dev', 'sign', 'log', 'abs', 'power', 'group_zscore', 
                 'group_rank', 'ts_delay', 'bucket', 'cap', 'vector_neut'}

    for entry in failure_data:
        msg = entry['message']
        expr = entry['expression']
        sharpe_val = 0
        try:
            sharpe_val = float(entry['sharpe'])
        except: pass

        # Extract fields used in this expression
        fields_in_expr = set([f for f in field_pattern.findall(expr) if f not in operators and not f.isdigit()])

        # 1. "Attempted to use unknown variable"
        match_unknown = re.search(r'unknown variable "([^"]+)"', msg)
        if match_unknown:
            unknown_vars.add(match_unknown.group(1))
        
        # 2. Generic "Unknown Platform Error" usually implies a field issue if message is vague
        elif "Unknown Platform Error" in msg or "Internal Server Error" in msg:
            # If the platform is silent, we suspect all fields in the failed expression
            unknown_vars.update(fields_in_expr)

        # 3. "does not support event inputs"
        if 'support event inputs' in msg:
            event_vars.update(fields_in_expr)

        # 4. "Incompatible unit"
        if 'Incompatible unit' in msg:
            incompatible_units.update(fields_in_expr)

    # Compile the ultimate blacklist
    ultimate_blacklist = unknown_vars | event_vars | incompatible_units | zero_sharpe_fields
    
    # 过滤掉常见的平台关键词（防止因日志截断导致误杀，如 subindust -> subindustry）
    keywords = {'subindustry', 'industry', 'sector', 'market', 'bucket', 'returns', 'rank', 'cap'}
    cleaned_blacklist = set()
    for f in ultimate_blacklist:
        if len(f) <= 3: continue
        if any(f in kw for kw in keywords): continue
        cleaned_blacklist.add(f)

    print(f"Discovered {len(unknown_vars)} unknown/inaccessible variables.")
    print(f"Discovered {len(event_vars)} event-type variables.")
    print(f"Discovered {len(incompatible_units)} incompatible unit variables.")
    
    with open('dynamic_blacklist.json', 'w') as f:
        json.dump(sorted(list(cleaned_blacklist)), f, indent=4)
    print(f"Saved {len(cleaned_blacklist)} fields to dynamic_blacklist.json")

if __name__ == "__main__":
    analyze_failures()
