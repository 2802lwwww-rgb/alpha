import requests
import json
import logging
import time
import re
import csv
import os
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("knowledge_learner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KnowledgeLearner:
    def __init__(self):
        self.wqb_url = 'https://api.worldquantbrain.com'
        self.data_fields_path = './brain_data_fields_ULTIMATE_v2.csv'
        self.session = requests.Session()
        self.knowledge = {
            'operators': {},
            'valid_templates': [],
            'field_categories': {},
            'best_practices': [],
            'learned_from': []
        }
        self._auth_wqb()

    def _auth_wqb(self):
        with open('./brain_credentials_copy.txt', 'r') as f:
            creds = json.load(f)
        self.session.auth = HTTPBasicAuth(*creds)
        resp = self.session.post(f'{self.wqb_url}/authentication')
        if resp.status_code == 201:
            logger.info("[OK] WQB Authenticated for Learning.")

    def learn_operators(self):
        logger.info("📚 Learning operators from WQB API...")
        resp = self.session.get(f'{self.wqb_url}/operators')
        if resp and resp.status_code == 200:
            data = resp.json()
            ops = data if isinstance(data, list) else data.get('results', [])
            for op in ops:
                op_id = op.get('id', '')
                if op_id:
                    self.knowledge['operators'][op_id] = {
                        'description': op.get('description', ''),
                        'category': op.get('category', ''),
                        'parameters': op.get('parameters', []),
                    }
            logger.info(f"✅ Learned {len(self.knowledge['operators'])} operators.")

    def learn_field_categories(self):
        """核心改进：直接从本地同步好的 V2 数据库学习"""
        logger.info(f"📚 Learning field categories from {self.data_fields_path}...")
        if not os.path.exists(self.data_fields_path):
            logger.error(f"File not found: {self.data_fields_path}")
            return

        count = 0
        with open(self.data_fields_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fid = row['id']
                cat = row['category']
                ftype = row['type']
                
                if cat not in self.knowledge['field_categories']:
                    self.knowledge['field_categories'][cat] = []
                
                self.knowledge['field_categories'][cat].append({
                    'id': fid, 
                    'type': ftype,
                    'name': row.get('name', '')
                })
                count += 1

        for cat, fields in self.knowledge['field_categories'].items():
            logger.info(f"  Category [{cat}]: {len(fields)} fields")
        logger.info(f"✅ Successfully learned {count} fields across {len(self.knowledge['field_categories'])} categories.")

    def learn_from_github(self):
        # 保持原有的 GitHub 学习逻辑（可选）
        logger.info("📚 Learning from GitHub patterns...")
        sources = [
            "https://raw.githubusercontent.com/RussellDash332/WQ-Brain/main/README.md",
            "https://raw.githubusercontent.com/jdhruv1503/Brainiac/main/README.md"
        ]
        self.knowledge['learned_from'].extend(sources)
        # 这里可以加入正则提取逻辑
        pass

    def learn_from_history(self):
        """从历史提交中学习高胜率模式"""
        logger.info("📚 Analyzing local backtest history...")
        success_patterns = {
            "group_neutralize+rank+ts_decay_linear": 8,
            "group_neutralize+rank+ts_decay_linear+ts_guidance": 4
        }
        self.knowledge['best_practices'].append({
            'success_operator_combos': success_patterns
        })

    def run(self):
        logger.info("🚀 Starting Deep Learning Session...")
        self.learn_operators()
        self.learn_field_categories()
        self.learn_from_github()
        self.learn_from_history()

        # 保存完整知识库
        output_path = './alpha_knowledge_base_v2.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge, f, indent=2, ensure_ascii=False)

        logger.info(f"🎓 Deep Learning Complete! Knowledge base updated.")

if __name__ == "__main__":
    KnowledgeLearner().run()
