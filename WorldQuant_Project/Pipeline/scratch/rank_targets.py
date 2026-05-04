import csv
import os

file_path = r"c:\Users\vv\Desktop\a\WorldQuant_Project\Pipeline\Candidates\optimization_targets.csv"

results = []

with open(file_path, 'r', encoding='utf-8') as f:
    # Use csv.reader to handle quotes
    reader = csv.reader(f)
    for row in reader:
        if not row or len(row) < 3:
            continue
        
        # Skip headers
        if row[0] == "expression" or "第二轮" in row[0]:
            continue
            
        try:
            expr = row[0]
            sharpe = float(row[1])
            fitness = float(row[2])
            turnover = float(row[3])
            score = sharpe * fitness
            results.append({
                'expression': expr,
                'sharpe': sharpe,
                'fitness': fitness,
                'turnover': turnover,
                'score': score
            })
        except (ValueError, IndexError):
            continue

# Sort by score descending
results.sort(key=lambda x: x['score'], reverse=True)

# Select top 30
top_30 = results[:30]

print("Rank | Score | Sharpe | Fitness | Turnover | Expression")
print("-" * 80)
for i, res in enumerate(top_30, 1):
    print(f"{i:2d} | {res['score']:.4f} | {res['sharpe']:.2f} | {res['fitness']:.2f} | {res['turnover']:.4f} | {res['expression']}")
