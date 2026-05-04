"""
10_AI_Alpha_Backtest.py - AI精修因子批量回测器 (多线程联动版)
读取 ai_crafted_alphas_v2.csv，使用三线程并行提交 WQB 回测。
"""
import requests, json, csv, time, os, logging, threading, math
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('ai_backtest.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIAlphaBacktester:
    def __init__(self):
        self.base_url = 'https://api.worldquantbrain.com'
        # [联动核心] 指向新矿机生成的 CSV 文件
        self.input_file = './ai_crafted_alphas_v2.csv' 
        self.result_file = './ai_backtest_results.csv'
        self.golden_file = './ra_final_results.csv'
        self.session = requests.Session()
        self.write_lock = threading.Lock()
        self.authenticate()

    def authenticate(self):
        try:
            # 兼容不同目录层级的凭证查找
            cred_path = '../brain_credentials_copy.txt' if os.path.exists('../brain_credentials_copy.txt') else './brain_credentials_copy.txt'
            if not os.path.exists(cred_path):
                logger.error(f"找不到凭证文件: {cred_path}")
                return
            with open(cred_path, 'r') as f:
                creds = json.load(f)
            self.session.auth = HTTPBasicAuth(*creds)
            resp = self.session.post(f'{self.base_url}/authentication')
            if resp.status_code == 201:
                logger.info("[OK] AI Backtester Authenticated.")
            else:
                logger.error(f"[ERROR] Auth Failed: {resp.status_code} | {resp.text}")
        except Exception as e:
            logger.error(f"[ERROR] Auth Exception: {e}")

    def _request(self, method, url, **kwargs):
        for attempt in range(5):
            try:
                resp = self.session.request(method, url, timeout=60, **kwargs)
                if resp.status_code in [401, 403]:
                    logger.warning(f"Session issue ({resp.status_code}), re-authenticating... (Attempt {attempt+1})")
                    self.authenticate()
                    continue
                if resp.status_code == 429:
                    logger.warning(f"Rate limited (Attempt {attempt+1}), waiting 65s...")
                    time.sleep(65)
                    continue
                return resp
            except Exception as e:
                logger.warning(f"Request exception (Attempt {attempt+1}/5): {e}")
                time.sleep(15)
        return None

    def run_simulation(self, expr, desc, settings_override=None):
        settings = {
            'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
            'delay': 1, 'decay': 0, 'neutralization': 'SUBINDUSTRY',
            'truncation': 0.08, 'pasteurization': 'ON', 'unitHandling': 'VERIFY',
            'nanHandling': 'OFF', 'language': 'FASTEXPR', 'visualization': False
        }
        if settings_override: settings.update(settings_override)

        payload = {'type': 'REGULAR', 'settings': settings, 'regular': expr}
        resp = self._request('POST', f'{self.base_url}/simulations', json=payload)

        if resp and resp.status_code == 201:
            loc = resp.headers.get('Location')
            for _ in range(30):
                time.sleep(20)
                p_resp = self._request('GET', loc)
                if p_resp and p_resp.status_code == 200:
                    try: data = p_resp.json()
                    except ValueError: continue
                        
                    status = data.get('status')
                    if status == 'COMPLETE':
                        alpha_id = data.get('alpha')
                        if isinstance(alpha_id, list): alpha_id = alpha_id[0]
                        a_resp = self._request('GET', f'{self.base_url}/alphas/{alpha_id}')
                        if a_resp:
                            try: a_data = a_resp.json()
                            except ValueError: continue
                                
                            m = a_data.get('is', {})
                            sub_sharpe = 0.0
                            for check in m.get('checks', []):
                                if check.get('name') == 'LOW_SUB_UNIVERSE_SHARPE':
                                    sub_sharpe = float(check.get('value', 0))
                                    break

                            res = {
                                's': float(m.get('sharpe', 0)), 't': float(m.get('turnover', 0)),
                                'f': float(m.get('fitness', 0)), 'r': float(m.get('returns', 0)),
                                'd': float(m.get('drawdown', 0)), 'm': float(m.get('margin', 0)),
                                'sub_s': sub_sharpe, 'sc': 0.0
                            }
                            
                            dynamic_thresh = 0.75 * math.sqrt(1000/3000) * abs(res['s'])
                            sub_s_passed = abs(res['sub_s']) >= dynamic_thresh
                            
                            if abs(res['s']) > 1.25 and abs(res['f']) > 1.0 and sub_s_passed:
                                time.sleep(5)
                                clean_id = str(alpha_id).strip().replace("['", "").replace("']", "")
                                check_url = f'{self.base_url}/alphas/{clean_id}/correlations/self'
                                
                                for _ in range(10):
                                    time.sleep(15)
                                    cp_resp = self._request('GET', check_url)
                                    if cp_resp and cp_resp.status_code == 200:
                                        try: cp_data = cp_resp.json()
                                        except ValueError: continue
                                        if isinstance(cp_data, dict) and 'max' in cp_data:
                                            res['sc'] = cp_data.get('max')
                                            break
                            
                            logger.info(f"FINAL | {expr} | Sharpe: {res['s']:.2f} | Fit: {res['f']:.2f} | SC: {res['sc']:.4f}")
                            self.save_result(expr, res, desc, settings)
                            
                            if res['s'] >= 1.25 and res['f'] >= 1.1 and res['sc'] <= 0.5 and abs(res['sub_s']) >= dynamic_thresh:
                                logger.info(f"★★★ [GOLDEN RA FOUND] ★★★ : {expr} (SC SAFE: {res['sc']:.4f})")
                                self.save_golden(expr, res, desc, settings)
                            elif res['sc'] >= 0.7:
                                logger.warning(f"⚠️ [HIGH SC] : {expr} SC is {res['sc']:.4f}")
                            return res
                        return None
                    elif status == 'ERROR':
                        logger.warning(f"SIM ERROR for {expr}")
                        return None
        return None

    def save_result(self, expr, res, desc, settings):
        with self.write_lock:
            first_write = not os.path.exists(self.result_file)
            with open(self.result_file, 'a', encoding='utf-8') as f:
                if first_write: f.write("expression,desc,sharpe,fitness,turnover,sub_sharpe,returns,drawdown,margin,self_corr,settings\n")
                f.write(f'"{expr}","{desc}",{res["s"]},{res["f"]},{res["t"]},{res["sub_s"]},{res["r"]},{res["d"]},{res["m"]},{res["sc"]},"{settings}"\n')

    def save_golden(self, expr, res, desc, settings):
        with self.write_lock:
            first_write = not os.path.exists(self.golden_file)
            with open(self.golden_file, 'a', encoding='utf-8') as f:
                if first_write: f.write("expression,desc,sharpe,fitness,turnover,sub_sharpe,returns,drawdown,margin,self_corr,settings\n")
                f.write(f'"{expr}","{desc}",{res["s"]},{res["f"]},{res["t"]},{res["sub_s"]},{res["r"]},{res["d"]},{res["m"]},{res["sc"]},"{settings}"\n')

    def process_item(self, row):
        try: self.run_simulation(row['expression'], row.get('desc', ''))
        except Exception as e: logger.error(f"Worker Error: {e}")

    def run(self):
        import pandas as pd
        if not os.path.exists(self.input_file):
            logger.error(f"输入文件未找到: {self.input_file}。请先运行 05_AI_Grandmaster_Miner.py 生成因子。")
            return

        df = pd.read_csv(self.input_file)
        logger.info(f"Loaded {len(df)} AI-crafted alphas. Starting 3-thread backtest...")

        with ThreadPoolExecutor(max_workers=3) as executor:
            items = [row for _, row in df.iterrows()]
            executor.map(self.process_item, items)

        logger.info(f"\n=== AI Multi-Thread Backtest Complete! Results saved to {self.result_file} ===")

if __name__ == "__main__":
    AIAlphaBacktester().run()
