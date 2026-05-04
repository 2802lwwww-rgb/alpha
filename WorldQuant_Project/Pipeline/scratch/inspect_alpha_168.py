import requests
import json
from requests.auth import HTTPBasicAuth

def find_and_inspect_alpha():
    base_url = 'https://api.worldquantbrain.com'
    credentials_path = './brain_credentials_copy.txt'
    
    with open(credentials_path, 'r') as f:
        creds = json.load(f)
    
    session = requests.Session()
    session.auth = HTTPBasicAuth(*creds)
    session.post(f'{base_url}/authentication')
    
    # 1. 查找夏普为 1.68 的因子
    print("Searching for Alpha with Sharpe 1.68...")
    resp = session.get(f'{base_url}/users/self/alphas?limit=100')
    if resp.status_code == 200:
        alphas = resp.json().get('results', [])
        target_alpha = None
        for a in alphas:
            sharpe = a.get('is', {}).get('sharpe')
            if sharpe and abs(float(sharpe) - 1.68) < 0.01:
                target_alpha = a
                break
        
        if target_alpha:
            alpha_id = target_alpha['id']
            print(f"Found Alpha ID: {alpha_id}")
            
            # 2. 深入抓取详情
            detail_resp = session.get(f'{base_url}/alphas/{alpha_id}')
            if detail_resp.status_code == 200:
                data = detail_resp.json()
                # 打印整个 'is' 模块，寻找 sub-universe
                print("\n--- IS Metrics ---")
                print(json.dumps(data.get('is', {}), indent=2))
                
                # 特别寻找 sub-universe 列表
                sub_universes = data.get('is', {}).get('sub-universes', [])
                if sub_universes:
                    print("\n--- Sub-Universe Details ---")
                    for sub in sub_universes:
                        print(f"Name: {sub.get('name')}, Sharpe: {sub.get('sharpe')}")
                else:
                    print("\nNo 'sub-universes' found in 'is' root. Checking other fields...")
                    # 有时候在 check 或者 tests 列表里
                    for key in data.keys():
                        if 'test' in key.lower() or 'check' in key.lower():
                            print(f"\nChecking key: {key}")
                            print(json.dumps(data[key], indent=2))
        else:
            print("Alpha with Sharpe 1.68 not found in the latest 100 alphas.")

if __name__ == "__main__":
    find_and_inspect_alpha()
