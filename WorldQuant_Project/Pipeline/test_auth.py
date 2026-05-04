import requests
import json
from requests.auth import HTTPBasicAuth

try:
    with open('./brain_credentials_copy.txt', 'r') as f:
        creds = json.load(f)
    print(f"Credentials loaded: {creds[0]}")
    resp = requests.post('https://api.worldquantbrain.com/authentication', auth=HTTPBasicAuth(*creds), timeout=15)
    print(f"Auth Status: {resp.status_code}")
    print(f"Response: {resp.text[:100]}")
except Exception as e:
    print(f"TEST FAILED: {e}")
