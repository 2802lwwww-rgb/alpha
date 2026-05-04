import requests
import json
import pandas as pd
import time
import sys
from requests.auth import HTTPBasicAuth

def scrape_everything():
    print("--- WorldQuant Brain 'Scrape Everything' Operation Start ---", flush=True)
    base_url = 'https://api.worldquantbrain.com'
    credentials_path = 'brain_credentials_copy.txt'
    
    try:
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
    except Exception as e:
        print(f"Error reading credentials: {e}", flush=True)
        return

    session = requests.Session()
    session.auth = HTTPBasicAuth(*creds)
    
    print("Step 1: Authenticating...", flush=True)
    auth_resp = session.post(f'{base_url}/authentication')
    if auth_resp.status_code != 201:
        print(f"Auth Failed: {auth_resp.status_code}", flush=True)
        return
    print("[OK] Authenticated Successfully", flush=True)

    # Step 2: Discovery of all Dataset IDs
    print("Step 2: Discovering Dataset IDs...", flush=True)
    dataset_ids = set()
    
    # Discovery via many keywords
    discovery_keywords = [
        'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z',
        'fundamental', 'analyst', 'price', 'volume', 'news', 'sentiment', 'esg', 'model', 'options', 'social', 
        'supply', 'customer', 'inventory', 'credit', 'macro', 'index', 'etf', 'sector'
    ]
    
    for kw in discovery_keywords:
        url = (f"{base_url}/data-fields?search={kw}"
               f"&region=USA&delay=1&universe=TOP3000"
               f"&instrumentType=EQUITY&limit=50")
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                for f in results:
                    d = f.get('dataset', {})
                    if isinstance(d, dict) and 'id' in d:
                        dataset_ids.add(d['id'])
            sys.stdout.write(f"\rDiscovered {len(dataset_ids)} datasets using keywords... ")
            sys.stdout.flush()
        except:
            pass
    print(f"\n[OK] Final count of discovered datasets: {len(dataset_ids)}")

    # Step 3: Scrape Every Single Field
    print("Step 3: Exhaustive field extraction by Dataset ID...", flush=True)
    all_fields_dict = {}
    
    # Load previous to keep progress
    for csv_file in ['brain_data_fields_all.csv', 'brain_data_fields_ULTIMATE.csv']:
        try:
            old_df = pd.read_csv(csv_file)
            for _, row in old_df.iterrows():
                # We need to handle the 'dataset' string if it was loaded as string
                f_id = row['id']
                all_fields_dict[f_id] = row.to_dict()
        except:
            pass
    print(f"Loaded {len(all_fields_dict)} fields from previous sessions.", flush=True)

    for d_id in sorted(list(dataset_ids)):
        print(f"Scraping dataset: {d_id}...", flush=True)
        offset = 0
        limit = 50
        while True:
            url = f"{base_url}/data-fields?dataset={d_id}&region=USA&delay=1&universe=TOP3000&limit={limit}&offset={offset}"
            try:
                resp = session.get(url, timeout=20)
                if resp.status_code == 429:
                    time.sleep(15)
                    continue
                if resp.status_code != 200: break
                
                data = resp.json()
                results = data.get('results', [])
                if not results: break
                
                for f in results:
                    all_fields_dict[f['id']] = f
                
                if len(results) < limit: break
                offset += limit
                time.sleep(0.1)
            except Exception as e:
                print(f"Error scraping {d_id}: {e}", flush=True)
                break
        print(f"Current total unique fields: {len(all_fields_dict)}", flush=True)

    # Final Save
    if all_fields_dict:
        all_fields = list(all_fields_dict.values())
        df_fields = pd.DataFrame(all_fields)
        if 'dataset' in df_fields.columns:
            # Handle mixed types (dict vs string-dict)
            def extract_id(x):
                if isinstance(x, dict): return x.get('id')
                if isinstance(x, str) and 'id' in x:
                    try:
                        # Simple extraction from string representation
                        import ast
                        return ast.literal_eval(x).get('id')
                    except: return x
                return x
            df_fields['dataset_id'] = df_fields['dataset'].apply(extract_id)
        
        df_fields.to_csv('brain_data_fields_ULTIMATE.csv', index=False)
        print(f"\n[SUCCESS] Scraped {len(all_fields)} fields in total.", flush=True)
        print("Check: brain_data_fields_ULTIMATE.csv", flush=True)
    else:
        print("[Error] No data collected.", flush=True)

if __name__ == "__main__":
    scrape_everything()
