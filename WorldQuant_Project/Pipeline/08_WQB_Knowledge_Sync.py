import requests
import json
import logging
import time
import csv
import urllib3
from requests.auth import HTTPBasicAuth

# 禁用安全警告（为了应对不稳定的 SSL 握手）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class WQBSyncResilient:
    def __init__(self):
        self.base_url = 'https://api.worldquantbrain.com'
        self.credentials_path = './brain_credentials_copy.txt'
        self.kb_path = './brain_knowledge_base_ULTIMATE.json'
        self.csv_path = 'brain_data_fields_ULTIMATE_v2.csv'
        self.session = requests.Session()
        self.authenticate()
        
        self.categories = [
            'model', 'sentiment', 'option', 'analyst', 
            'fundamental', 'news', 'pv', 'socialmedia'
        ]

    def authenticate(self):
        try:
            with open(self.credentials_path, 'r') as f:
                creds = json.load(f)
            self.session.auth = HTTPBasicAuth(*creds)
            self.session.post(f'{self.base_url}/authentication', verify=False)
            logger.info("[OK] Authenticated for Resilient Sync.")
        except Exception as e:
            logger.error(f"Auth error: {e}")

    def safe_request(self, url):
        """抗压型请求函数：处理 SSL、429、Timeout 等各种意外"""
        for attempt in range(10): # 增加重试次数
            try:
                resp = self.session.get(url, timeout=45, verify=False)
                if resp.status_code == 429:
                    logger.warning("Rate limit hit! Waiting 65s...")
                    time.sleep(66)
                    continue
                if resp.status_code == 200:
                    return resp
                logger.error(f"Request failed: {resp.status_code}")
                time.sleep(5)
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Connection/SSL Error: {e}. Retrying in 10s... ({attempt+1}/10)")
                time.sleep(10)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)
        return None

    def fetch_category_fields(self, category):
        logger.info(f"===> HARVESTING: {category.upper()}")
        fields = []
        offset = 0
        limit = 50
        
        while True:
            url = f"{self.base_url}/data-fields?category={category}&region=USA&delay=1&universe=TOP3000&instrumentType=EQUITY&limit={limit}&offset={offset}"
            resp = self.safe_request(url)
            if not resp: break
            
            data = resp.json()
            results = data.get('results', [])
            if not results: break
            
            for f in results:
                fields.append({
                    'id': f['id'],
                    'name': f.get('name'),
                    'category': category,
                    'dataset': f.get('dataset', {}).get('id') if isinstance(f.get('dataset'), dict) else None,
                    'type': f.get('type'),
                    'description': f.get('description', '').replace('\n', ' ')
                })
            
            logger.info(f"    - {category}: {len(fields)} fields so far...")
            if len(results) < limit: break
            offset += limit
            time.sleep(1.5)
            
        return fields

    def run(self):
        # 如果文件已存在，先读取已有数据实现去重
        existing_ids = set()
        all_data = []
        if os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        existing_ids.add(row['id'])
                        all_data.append(row)
                logger.info(f"Loaded {len(existing_ids)} existing fields from CSV.")
            except: pass

        for cat in self.categories:
            cat_fields = self.fetch_category_fields(cat)
            for f in cat_fields:
                if f['id'] not in existing_ids:
                    all_data.append(f)
                    existing_ids.add(f['id'])
            
            # 每抓完一个类目立刻保存一次，防止白干
            keys = ['id', 'name', 'category', 'dataset', 'type', 'description']
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(all_data)
            logger.info(f"CHECKPOINT: {cat.upper()} archived. Total size: {len(all_data)}")

        logger.info("="*50)
        logger.info(f"MISSION SUCCESS: {len(all_data)} TOTAL FIELDS SYNCED.")
        logger.info("="*50)

if __name__ == "__main__":
    import os
    WQBSyncResilient().run()
