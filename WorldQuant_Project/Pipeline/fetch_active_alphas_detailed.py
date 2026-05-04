import requests
import json
import csv
import os
import time
from requests.auth import HTTPBasicAuth

class WQBAlphaFetcher:
    def __init__(self):
        self.base_url = 'https://api.worldquantbrain.com'
        self.credentials_path = './brain_credentials_copy.txt'
        self.output_file = './submitted_alphas_detailed.csv'
        self.session = requests.Session()
        self.authenticate()

    def authenticate(self):
        if not os.path.exists(self.credentials_path):
            print(f"Error: Credentials file not found at {self.credentials_path}")
            return False
        with open(self.credentials_path, 'r') as f:
            creds = json.load(f)
        self.session.auth = HTTPBasicAuth(*creds)
        resp = self.session.post(f'{self.base_url}/authentication')
        if resp.status_code == 201:
            print("[OK] Authenticated successfully.")
            return True
        else:
            print(f"Failed to authenticate. Status: {resp.status_code}")
            return False

    def fetch_active_alphas(self):
        print("Fetching active alphas...")
        active_alphas = []
        limit = 50
        offset = 0
        
        while True:
            url = f'{self.base_url}/users/self/alphas?limit={limit}&offset={offset}'
            resp = self.session.get(url)
            if resp.status_code != 200:
                print(f"Error fetching alphas: {resp.status_code}")
                break
            
            data = resp.json()
            results = data.get('results', [])
            if not results:
                break
            
            for alpha in results:
                # 过滤状态
                if alpha.get('status') != 'ACTIVE':
                    continue
                
                alpha_id = alpha.get('id')
                
                # 获取基本面指标 (In-Sample Metrics)
                m = alpha.get('is', {})
                
                # 试图提取现成的自相关性
                sc_val = m.get('selfCorrelation')
                if sc_val is None:
                    # 如果列表里不带这个数据，我们就亲自去查真实的底层接口
                    time.sleep(2)  # 防止请求过快被限流
                    try:
                        c_resp = self.session.get(f'{self.base_url}/alphas/{alpha_id}/correlations/self', timeout=10)
                        if c_resp.status_code == 200:
                            c_data = c_resp.json()
                            if isinstance(c_data, dict) and 'max' in c_data:
                                sc_val = c_data.get('max')
                    except Exception as e:
                        print(f"Error fetching SC for {alpha_id}: {e}")
                
                sc_val = sc_val if sc_val is not None else 0.0
                
                # 获取设置 (Settings)
                s = alpha.get('settings', {})
                
                alpha_data = {
                    'id': alpha_id,
                    'expression': alpha.get('regular'),
                    'sharpe': m.get('sharpe'),
                    'fitness': m.get('fitness'),
                    'turnover': m.get('turnover'),
                    'returns': m.get('returns'),
                    'drawdown': m.get('drawdown'),
                    'margin': m.get('margin'),
                    'sc': sc_val,
                    'universe': s.get('universe'),
                    'decay': s.get('decay'),
                    'neutralization': s.get('neutralization'),
                    'truncation': s.get('truncation'),
                    'region': s.get('region'),
                    'date_submitted': alpha.get('dateCreated', '')[:10]
                }
                active_alphas.append(alpha_data)
            
            if len(results) < limit:
                break
            offset += limit
            
        return active_alphas

    def save_to_csv(self, alphas):
        if not alphas:
            print("No active alphas found to save.")
            return

        keys = alphas[0].keys()
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(alphas)
        print(f"[Success] Saved {len(alphas)} active alphas to {self.output_file}")

if __name__ == "__main__":
    fetcher = WQBAlphaFetcher()
    active_list = fetcher.fetch_active_alphas()
    fetcher.save_to_csv(active_list)
