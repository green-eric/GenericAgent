#!/usr/bin/env python3
"""
Simple IMA sync test
"""

import os
import json
import sys
import datetime
import requests
from pathlib import Path

# Config paths
CONFIG_DIR = Path.home() / ".config" / "ima"
CLIENT_ID_FILE = CONFIG_DIR / "client_id"
API_KEY_FILE = CONFIG_DIR / "api_key"

# IMA API endpoints
IMA_BASE_URL = "https://ima.qq.com/openapi"
IMPORT_DOC_URL = f"{IMA_BASE_URL}/note/v1/import_doc"
LIST_NOTEBOOK_URL = f"{IMA_BASE_URL}/note/v1/list_notebook"

def load_credentials():
    """Load IMA API credentials"""
    if not CLIENT_ID_FILE.exists():
        raise FileNotFoundError(f"Client ID file not found: {CLIENT_ID_FILE}")
    if not API_KEY_FILE.exists():
        raise FileNotFoundError(f"API Key file not found: {API_KEY_FILE}")
    
    with open(CLIENT_ID_FILE, 'r', encoding='utf-8') as f:
        client_id = f.read().strip()
    
    with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
        api_key = f.read().strip()
    
    return client_id, api_key

def test_connection(client_id, api_key):
    """Test IMA API connection"""
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'ima-openapi-ctx': 'skill_version=1.1.3',
        'Content-Type': 'application/json'
    }
    
    payload = {"cursor": "0", "limit": 10}
    
    try:
        response = requests.post(LIST_NOTEBOOK_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"Response code: {result.get('code')}")
        print(f"Response message: {result.get('message')}")
        
        if result.get("code") != 0:
            print(f"API error: {result.get('message', 'Unknown error')}")
            return False
        
        data = result.get("data", {})
        notebooks = data.get("note_book_folders", [])
        print(f"Found {len(notebooks)} notebooks")
        
        for i, nb in enumerate(notebooks):
            folder_info = nb.get("folder", {}).get("basic_info", {})
            print(f"  {i+1}. {folder_info.get('name')} (ID: {folder_info.get('folder_id')})")
        
        return True
        
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def sync_memory(client_id, api_key):
    """Sync today's work memory"""
    workspace_root = Path(__file__).parent
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    memory_file = workspace_root / ".workbuddy" / "memory" / f"{today}.md"
    
    if not memory_file.exists():
        print(f"Today's memory file not found: {memory_file}")
        return None
    
    with open(memory_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print("Memory file is empty")
        return None
    
    title = f"WorkBuddy Work Memory - {today}"
    full_content = f"# {title}\n\n{content}"
    
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'ima-openapi-ctx': 'skill_version=1.1.3',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "content_format": 1,
        "content": full_content
    }
    
    print(f"Syncing memory: {title}")
    print(f"Content length: {len(content)} characters")
    
    try:
        response = requests.post(IMPORT_DOC_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"Response code: {result.get('code')}")
        print(f"Response message: {result.get('message')}")
        
        if result.get("code") != 0:
            print(f"Create note failed: {result.get('message', 'Unknown error')}")
            return None
        
        doc_id = result.get("data", {}).get("doc_id")
        if not doc_id:
            print("Create note failed: No doc_id returned")
            return None
        
        print(f"Success! Note ID: {doc_id}")
        return doc_id
        
    except Exception as e:
        print(f"Sync failed: {e}")
        return None

def main():
    print("=== IMA WeChat Mini Program Sync Test ===")
    print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Load credentials
        client_id, api_key = load_credentials()
        print("1. Credentials loaded: OK")
        
        # Test connection
        print("2. Testing API connection...")
        if not test_connection(client_id, api_key):
            print("Connection test failed, aborting.")
            return
        
        # Sync memory
        print("3. Syncing today's work memory...")
        doc_id = sync_memory(client_id, api_key)
        
        if doc_id:
            print()
            print("=== Sync Completed ===")
            print("You can view the synced content in WeChat IMA Mini Program:")
            print("1. Open WeChat, search for 'IMA Mini Program'")
            print("2. Log in with the same account")
            print("3. Look for note titled 'WorkBuddy Work Memory - 2026-04-18'")
            print()
            print("Note: If a note with the same title already exists, a new note will be created.")
        else:
            print("Sync not completed")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()