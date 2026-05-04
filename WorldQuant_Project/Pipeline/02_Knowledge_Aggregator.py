import requests
import json
import time
from requests.auth import HTTPBasicAuth

def aggregate_knowledge():
    print("--- 02_Knowledge_Aggregator: WorldQuant Brain Knowledge Base Mirror ---")
    base_url = 'https://api.worldquantbrain.com'
    credentials_path = 'brain_credentials_copy.txt'
    
    try:
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
    except Exception as e:
        print(f"Error reading credentials: {e}")
        return

    session = requests.Session()
    session.auth = HTTPBasicAuth(*creds)
    
    print("Authenticating...")
    auth_resp = session.post(f'{base_url}/authentication')
    if auth_resp.status_code != 201:
        print(f"Auth Failed: {auth_resp.status_code}")
        return
    print("Authenticated Successfully. Fetching Operators...")

    operators_dict = {}
    
    # WorldQuant Brain exposes /operators which returns all valid operators
    url = f"{base_url}/operators"
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            for op in data:
                # Store the operator signature, category, and description
                op_name = op.get('name')
                operators_dict[op_name] = {
                    'description': op.get('description', ''),
                    'category': op.get('category', ''),
                    'args': op.get('args', [])
                }
            print(f"Successfully scraped {len(operators_dict)} operators from the platform.")
        else:
            print(f"Failed to fetch operators. Status Code: {resp.status_code}")
    except Exception as e:
        print(f"Error fetching operators: {e}")

    # Synthesize "Best Practices" mapping
    # This acts as the "Brain" mapping fields to appropriate operators
    best_practices = {
        "residual_stripping": "ts_regression(rank(target), returns, 252)",
        "volume_breakout": "rank(vwap / close) * rank(volume / ts_mean(volume, 60))",
        "inventory_liability_reversal": "-1 * ts_delta(target, 20) / ts_std_dev(target, 60)",
        "cross_dataset_validation": "ts_zscore(analyst_field, 60) * ts_rank(sentiment_field, 60)"
    }
    
    knowledge_base = {
        "timestamp": time.time(),
        "operators": operators_dict,
        "best_practices_templates": best_practices
    }
    
    with open('brain_knowledge_base.json', 'w') as f:
        json.dump(knowledge_base, f, indent=4)
        
    print("Knowledge base successfully updated and saved to brain_knowledge_base.json")
    print("The 04_Alpha_Miner script can now use this JSON to ensure it is using valid and optimal operators.")

if __name__ == "__main__":
    aggregate_knowledge()
