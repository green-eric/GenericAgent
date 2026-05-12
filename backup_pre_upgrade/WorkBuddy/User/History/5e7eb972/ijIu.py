#!/usr/bin/env python3
"""
Debug IMA sync
"""

import json
import requests
from pathlib import Path

# Config paths
CONFIG_DIR = Path.home() / ".config" / "ima"
CLIENT_ID_FILE = CONFIG_DIR / "client_id"
API_KEY_FILE = CONFIG_DIR / "api_key"

# IMA API endpoints
IMA_BASE_URL = "https://ima.qq.com/openapi"
IMPORT_DOC_URL = f"{IMA_BASE_URL}/note/v1/import_doc"

def load_credentials():
    """Load IMA API credentials"""
    with open(CLIENT_ID_FILE, 'r', encoding='utf-8') as f:
        client_id = f.read().strip()
    
    with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
        api_key = f.read().strip()
    
    return client_id, api_key

def main():
    client_id, api_key = load_credentials()
    
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'ima-openapi-ctx': 'skill_version=1.1.3',
        'Content-Type': 'application/json'
    }
    
    # Test with minimal content
    payload = {
        "content_format": 1,
        "content": "# Test Note\n\nThis is a test note from WorkBuddy."
    }
    
    print("Request headers:", json.dumps(headers, indent=2))
    print("Request payload:", json.dumps(payload, indent=2))
    
    try:
        response = requests.post(IMPORT_DOC_URL, headers=headers, data=json.dumps(payload), timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        # Try to parse JSON
        try:
            result = response.json()
            print("Response JSON:", json.dumps(result, indent=2, ensure_ascii=False))
        except:
            print(f"Response text (not JSON): {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()