import os
import csv
import json
import random
import logging
import re
import time
import requests
from requests.auth import HTTPBasicAuth
from openai import OpenAI  # 切换到 OpenAI 库
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('ai_miner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GrandmasterPlaybookMiner:
    def __init__(self):
        self.fields_path = './brain_data_fields_ULTIMATE_v2.csv'
        self.output_path = './Candidates/ai_crafted_alphas_v2.csv'
        self.cloud_cache_file = './cloud_history_cache.txt'
        
        self.fields_by_cat = {
            'model': [], 'sentiment': [], 'analyst': [], 'news': [],
            'fundamental': [], 'price': [], 'volume': [], 'option': []
        }
        
        # 1. 初始化 OpenAI 兼容接口 (Gemini-3-Flash)
        self.client = OpenAI(
            base_url="http://127.0.0.1:8045/v1",
            api_key="sk-0e818065ef764ea78092ace8112201c5"
        )
        self.model_name = "gemini-3-flash"
        
        # 2. 初始化 WQB API (用于云端同步查重)
        self.wqb_base_url = 'https://api.worldquantbrain.com'
        self.session = requests.Session()
        self.authenticate_wqb()
        
        # 3. 加载全维度的历史去重库和字段池
        self.history_alphas = set()
        self.load_history()
        self.load_local_fields()

    def authenticate_wqb(self):
        try:
            cred_path = './brain_credentials_copy.txt'
            if not os.path.exists(cred_path):
                logger.error(f"找不到凭证文件: {cred_path}")
                return
            with open(cred_path, 'r') as f:
                creds = json.load(f)
            self.session.auth = HTTPBasicAuth(*creds)
            resp = self.session.post(f'{self.wqb_base_url}/authentication')
            if resp.status_code == 201:
                logger.info("🔑 WQB 平台授权成功，准备同步云端防重库。")
            else:
                logger.error("WQB 授权失败，云端同步受限。")
        except Exception as e:
            logger.error(f"加载 WQB 凭证失败: {e}")

    def _request_wqb(self, method, url, **kwargs):
        for _ in range(3):
            try:
                resp = self.session.request(method, url, timeout=45, **kwargs)
                if resp.status_code in [401, 403]:
                    self.authenticate_wqb()
                    continue
                return resp
            except Exception:
                time.sleep(5)
        return None

    def load_history(self):
        history_files = [
            'sprint_results_v6.csv',
            'submitted_alphas_detailed.csv',
            './Candidates/ra_final_results.csv',
            './Candidates/ai_backtest_results.csv', # 将刚刚失败的记录也加入黑名单
            self.output_path,
            self.cloud_cache_file
        ]
        for file_path in history_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if file_path.endswith('.txt'):
                            for line in f:
                                if expr := line.strip(): self.history_alphas.add(expr)
                        else:
                            for row in csv.DictReader(f):
                                expr = row.get('expression') or row.get('regular') or row.get('Expression')
                                if expr: self.history_alphas.add(str(expr).strip())
                except: pass
        logger.info(f"📂 历史黑名单加载完毕，当前拦截容量: {len(self.history_alphas)} 条。")
        self._sync_platform_history_incremental()

    def _sync_platform_history_incremental(self):
        logger.info("☁️ 正在执行云端增量同步...")
        new_cloud_alphas = 0
        if not os.path.exists(self.cloud_cache_file): open(self.cloud_cache_file, 'w').close()

        with open(self.cloud_cache_file, 'a', encoding='utf-8') as cache_file:
            for status in ['ACTIVE', 'UNSUBMITTED', 'DECOMMISSIONED']:
                for offset in range(0, 10000, 100):
                    url = f'{self.wqb_base_url}/users/self/alphas?limit=100&offset={offset}&status={status}'
                    resp = self._request_wqb('GET', url)
                    if resp and resp.status_code == 200:
                        batch = resp.json().get('results', [])
                        if not batch: break
                        known_count = 0
                        for a in batch:
                            if expr := str(a.get('regular', '')).strip():
                                if expr in self.history_alphas: known_count += 1
                                else:
                                    self.history_alphas.add(expr)
                                    cache_file.write(expr + '\n')
                                    new_cloud_alphas += 1
                        if known_count == len(batch): break 
                    else: break
        logger.info(f"✅ 云端同步完成！新增 {new_cloud_alphas} 条记录。")

    def load_local_fields(self):
        blacklist = {'cap', 'sector', 'industry', 'subindustry', 'market', 'bucket', 'ticker', 'country'}
        if not os.path.exists(self.fields_path): return
        with open(self.fields_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                fid, cat = row.get('id'), row.get('category', 'unknown')
                if row.get('type') in ['MATRIX', 'SYMBOL'] and fid not in blacklist:
                    if cat in self.fields_by_cat: self.fields_by_cat[cat].append(fid)
        logger.info(f"📊 特征池加载完毕: { {k: len(v) for k, v in self.fields_by_cat.items()} }")

    def execute_playbook(self):
        # 强制高阶算子骨架与严苛周期
        playbooks = [
            {"logic_name": "时序相关性偏离反转", "pools": ['news', 'price', 'volume'], "inst": "寻找情绪或基本面特征与量价特征在时序上本应相关，却突然发生背离的标的。"},
            {"logic_name": "横截面波动率调整动量", "pools": ['fundamental', 'analyst', 'model'], "inst": "将长期基本面质量或分析师预期，除以其自身的历史波动率，寻找确定性高的低波动溢价。"},
            {"logic_name": "深层回归特质剥离", "pools": ['sentiment', 'option', 'fundamental'], "inst": "利用回归算子，将情绪或期权指标对基本面杠杆进行正交剥离。"}
        ]
        pb = random.choice(playbooks)
        
        # 精准抽取字段
        context_fields = {cat: random.sample(self.fields_by_cat[cat], min(8, len(self.fields_by_cat[cat]))) for cat in pb['pools'] if self.fields_by_cat.get(cat)}

        prompt = f"""
        你现在是一个 WorldQuant BRAIN 量化代码变异器。当前市场：USA TOP3000。
        请严格使用以下字段池进行填空组合：{json.dumps(context_fields, ensure_ascii=False)}
        
        【最高指令：严禁自由发挥结构！必须使用且仅使用以下三种数学骨架之一进行变异填空】
        
        骨架1 (时序背离):
        ts_decay_linear(group_neutralize(ts_correlation( [填入特征A] , [填入特征B] , [周期M] ), subindustry), [周期N])
        
        骨架2 (波动率惩罚的横截面):
        ts_decay_linear(group_neutralize(ts_rank( [填入特征A] , [周期M] ) / (ts_std_dev( [填入特征B] , [周期M] ) + 0.001), subindustry), [周期N])
        
        骨架3 (高阶时序残差):
        ts_decay_linear(group_neutralize(ts_regression( [填入特征A] , [填入特征B] , [周期M] , rettype=2), subindustry), [周期N])
        
        【极其关键的强制参数约束】
        1. [周期N] 是外层 decay 的天数，为了降换手率保证Fitness，必须在 20 到 60 之间随机取整数（绝不能小于20！）。
        2. [周期M] 是内层计算天数，必须在 60 到 252 之间取长周期整数。
        3. 所有被除数分母必须加上 0.001 防错。
        
        生成 20 个代码。仅输出 JSON 数组，包含 "expression"。不要 ```json 标记。
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.choices[0].message.content.strip()
            raw_text = re.sub(r'^```json\n|```\n?$', '', raw_text, flags=re.MULTILINE)
            alphas = json.loads(raw_text)
            return self.save_candidates(alphas)
        except Exception as e:
            logger.error(f"生成失败，大模型可能输出断裂: {e}")
            return 0

    def save_candidates(self, alphas):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        file_exists, valid_count = os.path.isfile(self.output_path), 0
        with open(self.output_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if not file_exists: writer.writerow(['expression'])
            for a in alphas:
                expr = str(a.get('expression', '')).replace('\n', ' ').strip()
                if expr and expr not in self.history_alphas:
                    writer.writerow([expr])
                    self.history_alphas.add(expr)
                    valid_count += 1
        logger.info(f"✅ 从模板变异中提取，实际写入 {valid_count} 个合规因子。")
        return valid_count

if __name__ == "__main__":
    miner = GrandmasterPlaybookMiner()
    for i in range(30):
        logger.info(f"--- 轮次 {i+1}/30 ---")
        miner.execute_playbook()
        time.sleep(random.uniform(3, 6)) # 缩短了冷却时间，因为本地代理通常更稳定
