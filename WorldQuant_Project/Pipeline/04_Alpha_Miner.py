import requests
import json
import time
import os
import random
import logging
import csv
import threading
import math
from concurrent.futures import ThreadPoolExecutor
from requests.auth import HTTPBasicAuth

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("sprint_miner_v6.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExpertAlphaMiner:
    def __init__(self):
        self.base_url = 'https://api.worldquantbrain.com'
        self.credentials_path = './brain_credentials_copy.txt'
        self.results_path = 'sprint_results_v6.csv'
        self.failure_path = 'sprint_failed_v6.csv'
        self.knowledge_path = './alpha_knowledge_base_v2.json'
        self.fields_path = './brain_data_fields_ULTIMATE_v2.csv'
        
        self.session = requests.Session()
        self.authenticate()
        self.load_resources()
        self.existing_alphas = self._deep_scan_history()
        self.lock = threading.Lock()

    def authenticate(self):
        with open(self.credentials_path, 'r') as f:
            creds = json.load(f)
        self.session.auth = HTTPBasicAuth(*creds)
        resp = self.session.post(f'{self.base_url}/authentication')
        if resp.status_code == 201:
            logger.info("[OK] Session Authenticated/Renewed.")
            return True
        else:
            logger.error(f"FATAL: Auth Failed {resp.status_code}.")
            os._exit(1)

    def load_resources(self):
        self.fields_by_cat = {}
        # 2. 先加载黑名单
        self.blacklist = {'cap', 'sector', 'industry', 'subindustry', 'market', 'bucket', 'ticker', 'country'}
        if os.path.exists('dynamic_blacklist.json'):
            try:
                with open('dynamic_blacklist.json', 'r') as f:
                    self.blacklist.update(json.load(f))
            except: pass
            
        # 1. 加载 5000+ 超级字段
        with open(self.fields_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                f_id = row.get('id')
                # 核心过滤：只允许 MATRIX/SYMBOL 类型，且排除黑名单字段
                if row.get('type') not in ['MATRIX', 'SYMBOL']: continue
                if f_id in self.blacklist: continue
                
                cat = row.get('category', 'unknown')
                if cat not in self.fields_by_cat: self.fields_by_cat[cat] = []
                self.fields_by_cat[cat].append(f_id)
        
        logger.info(f"Loaded {sum(len(v) for v in self.fields_by_cat.values())} safe fields.")

    def _sync_platform_history(self):
        """核心改进：多状态深度抓取，确保去重生效"""
        platform_alphas = set()
        logger.info("Syncing comprehensive alpha history from WQB...")
        
        # 尝试不带状态过滤抓取（通常返回 SUBMITTED/ACTIVE）
        for offset in range(0, 5000, 100):
            url = f'{self.base_url}/users/self/alphas?limit=100&offset={offset}'
            resp = self._request('GET', url)
            if resp and resp.status_code == 200:
                batch = resp.json().get('results', [])
                if not batch: break
                for a in batch:
                    expr = a.get('regular', '')
                    if expr: platform_alphas.add(str(expr).strip())
                if len(batch) < 100: break
            else: break
            
        # 单独尝试抓取 UNSUBMITTED 和 DECOMMISSIONED
        for status in ['UNSUBMITTED', 'DECOMMISSIONED']:
            for offset in range(0, 3000, 100):
                url = f'{self.base_url}/users/self/alphas?limit=100&offset={offset}&status={status}'
                resp = self._request('GET', url)
                if resp and resp.status_code == 200:
                    batch = resp.json().get('results', [])
                    if not batch: break
                    for a in batch:
                        expr = a.get('regular', '')
                        if expr: platform_alphas.add(str(expr).strip())
                    if len(batch) < 100: break
                else: break
        
        logger.info(f"Cloud Sync Complete: Found {len(platform_alphas)} history alphas.")
        return platform_alphas

    def _deep_scan_history(self):
        history = self._sync_platform_history()
        files = [f for f in os.listdir('.') if f.endswith('.csv')]
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        for col in ['expression', 'Expression', 'regular']:
                            if col in row: history.add(row[col].strip())
            except: pass
        return history

    def _request(self, method, url, **kwargs):
        for i in range(3):
            try:
                resp = self.session.request(method, url, timeout=45, **kwargs)
                if resp.status_code in [401, 403]:
                    self.authenticate()
                    time.sleep(2)
                    continue
                return resp
            except Exception as e:
                logger.warning(f"Net Error ({i+1}/3): {e}")
                time.sleep(5)
        return None

    def generate_expert_tasks(self):
        tasks = []
        f_model = self.fields_by_cat.get('model', [])
        f_sentiment = self.fields_by_cat.get('sentiment', [])
        f_analyst = self.fields_by_cat.get('analyst', [])
        f_news = self.fields_by_cat.get('news', [])
        f_fundamental = self.fields_by_cat.get('fundamental', [])
        f_price = self.fields_by_cat.get('price', [])
        f_volume = self.fields_by_cat.get('volume', [])
        f_option = self.fields_by_cat.get('option', [])

        all_strategic = []
        for cat in ['model', 'sentiment', 'analyst', 'news', 'fundamental', 'price', 'volume', 'option']:
            all_strategic.extend(self.fields_by_cat.get(cat, []))

        def add(expr, desc):
            if expr not in self.existing_alphas:
                tasks.append({'expr': expr, 'desc': desc})

        # 策略 1: 新闻残差
        if f_news or f_sentiment:
            pool = f_news + f_sentiment
            for _ in range(100):
                s = random.choice(pool)
                add(f"group_neutralize(ts_regression(returns, ts_backfill(vec_avg({s}), 20), 250, rettype=2), subindustry)", "2025 News Residual")

        # 策略 2: 峰值捕捉 (保留明星策略)
        if f_model:
            for m in random.sample(f_model, min(len(f_model), 150)):
                add(f"ts_decay_linear(group_rank(ts_arg_max(rank({m}), 60), subindustry), 40)", "Peak Timing Momentum")

        # 策略 3: 正交化 (使用 ts_regression 替代 orthogonalize)
        if len(all_strategic) >= 2:
            for _ in range(150):
                f1, f2 = random.sample(all_strategic, 2)
                # 使用 rettype=2 返回残差，效果等同于正交化
                add(f"ts_regression(rank({f1}), rank({f2}), 250, rettype=2)", "Residual Orthogonal")

        # 策略 4: 分析师分歧度
        if f_analyst:
            for a in random.sample(f_analyst, min(len(f_analyst), 100)):
                add(f"ts_decay_linear(group_zscore(ts_std_dev({a}, 20) / ts_mean({a}, 20), subindustry), 40)", "Analyst Dispersion")

        # 策略 5: 市值脱敏 (使用 ts_regression 替代 orthogonalize)
        if len(all_strategic) >= 2:
            for _ in range(150):
                f1, f2 = random.sample(all_strategic, 2)
                add(f"ts_decay_linear(ts_regression(rank({f1}), rank(cap), 250, rettype=2) * rank({f2}), 35)", "Large-Cap Robust Hybrid")

        # 策略 6: 因子相关性捕捉 (去掉了不支持的 delay 算子)
        for _ in range(150):
            f = random.choice(all_strategic)
            add(f"ts_decay_linear(group_neutralize(ts_corr(rank(close), rank({f}), 10), subindustry), 20)", "Factor Correlation")

        random.shuffle(tasks)
        return tasks[:800]

    def submit_and_poll(self, task):
        expr, desc = task['expr'], task['desc']
        settings = {
            'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
            'delay': 1, 'decay': 0, 'neutralization': 'SUBINDUSTRY',
            'truncation': 0.08, 'pasteurization': 'ON', 'unitHandling': 'VERIFY',
            'nanHandling': 'OFF', 'language': 'FASTEXPR', 'visualization': False
        }
        payload = {'type': 'REGULAR', 'settings': settings, 'regular': expr}
        
        resp = self._request('POST', f'{self.base_url}/simulations', json=payload)
        
        # 修复逻辑漏洞：使用 is not None 判断
        if resp is not None and resp.status_code == 201:
            loc = resp.headers.get('Location')
            for _ in range(20):
                time.sleep(35)
                p_resp = self._request('GET', loc)
                if p_resp is not None and p_resp.status_code == 200:
                    data = p_resp.json()
                    if data.get('status') == 'COMPLETE':
                        alpha_id = data.get('alpha')
                        if isinstance(alpha_id, list): alpha_id = alpha_id[0]
                        a_resp = self._request('GET', f'{self.base_url}/alphas/{alpha_id}')
                        if not a_resp: return
                        a_data = a_resp.json()
                        m = a_data.get('is', {})
                        s, f, t = float(m.get('sharpe', 0)), float(m.get('fitness', 0)), float(m.get('turnover', 0))
                        
                        sub_s = 0.0
                        for check in m.get('checks', []):
                            if check.get('name') == 'LOW_SUB_UNIVERSE_SHARPE':
                                sub_s = float(check.get('value', 0))
                                break

                        dynamic_sub_s_threshold = 0.75 * math.sqrt(1000/3000) * abs(s)
                        sc_val = 0.0
                        if abs(s) > 1.0 and abs(f) > 0.8 and abs(sub_s) >= dynamic_sub_s_threshold:
                            check_url = f'{self.base_url}/alphas/{alpha_id}/correlations/self'
                            for _ in range(10):
                                time.sleep(15)
                                cp_resp = self._request('GET', check_url)
                                if cp_resp:
                                    sc_data = cp_resp.json()
                                    if 'max' in sc_data:
                                        sc_val = sc_data['max']
                                        break
                        
                        # [NEW] 负值因子自动转正逻辑：检测到高价值负夏普则反转回测
                        if s < -0.99 and abs(f) > 0.8:
                            logger.info(f"检测到优质负因子 (S:{s:.2f}, F:{f:.2f}), 正在自动反转回测...")
                            flipped_task = {'expr': f"-1 * ({expr})", 'desc': f"{desc} [Auto-Flipped]"}
                            return self.submit_and_poll(flipped_task)

                        logger.info(f"FINISH | S: {s:.2f} | F: {f:.2f} | T: {t:.2f} | SubS: {sub_s:.2f} | SC: {sc_val:.4f} | {desc}")
                        self.save_result(expr, s, f, t, sub_s, sc_val, desc)
                        return
                    elif data.get('status') == 'ERROR':
                        err_msg = data.get('error') or data.get('message') or "Unknown Error"
                        logger.warning(f"SIM FAILED: {err_msg} | Expr: {expr}")
                        self.save_failure(expr, err_msg)
                        return
        elif resp is not None and resp.status_code == 429:
            logger.warning("429 Too Many Requests! Cooling down for 60s...")
            time.sleep(60)
        else:
            status = resp.status_code if resp is not None else "No Response"
            body = resp.text[:200] if resp is not None else "N/A"
            logger.error(f"Submit Failed | Code: {status} | Msg: {body} | Expr: {expr[:60]}")

    def save_failure(self, expr, err_msg):
        with self.lock:
            with open('sprint_failed_v6.csv', 'a', encoding='utf-8') as file:
                clean_reason = str(err_msg).replace('\n', ' ').replace('"', "'")
                file.write(f'"{expr}","{clean_reason}","ERROR"\n')

    def save_result(self, expr, s, f, t, sub_s, sc, desc):
        dynamic_threshold = 0.75 * math.sqrt(1000/3000) * abs(s)
        with self.lock:
            if abs(s) >= 1.25 and abs(f) >= 1.0 and abs(sub_s) >= dynamic_threshold and sc < 0.7 and t < 0.7:
                with open('golden_alphas_v6.csv', 'a', encoding='utf-8') as file:
                    file.write(f'"{expr}",{s},{f},{t},{sub_s},{sc},"{desc}"\n')
            with open('sprint_results_v6.csv', 'a', encoding='utf-8') as file:
                file.write(f'"{expr}",{s},{f},{t},{sub_s},{sc},"{desc}"\n')

    def run(self):
        tasks = self.generate_expert_tasks()
        logger.info(f"V7.8 High-Speed Online. Tasks: {len(tasks)}")
        # 恢复 3 线程，高效冲刺
        with ThreadPoolExecutor(max_workers=3) as executor:
            for task in tasks:
                # 8-15 秒休眠，这是单进程下的黄金安全区间
                time.sleep(random.uniform(5, 10))
                executor.submit(self.submit_and_poll, task)

if __name__ == "__main__":
    ExpertAlphaMiner().run()
