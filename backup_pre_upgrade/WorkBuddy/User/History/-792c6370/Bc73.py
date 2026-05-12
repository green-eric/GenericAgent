#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import os
import sys

# Read credentials from config files
config_dir = os.path.expanduser('~/.config/ima')
client_id_path = os.path.join(config_dir, 'client_id')
api_key_path = os.path.join(config_dir, 'api_key')

with open(client_id_path, 'r', encoding='utf-8') as f:
    client_id = f.read().strip()
with open(api_key_path, 'r', encoding='utf-8') as f:
    api_key = f.read().strip()

print(f'Client ID: {client_id[:8]}...')
print(f'API Key: {api_key[:8]}...')

# Read memory file
memory_path = os.path.join('c:/Users/green/WorkBuddy/Claw/.workbuddy/memory/2026-04-18.md')
with open(memory_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f'Memory content length: {len(content)} chars')

# Prepare headers
headers = {
    'ima-openapi-clientid': client_id,
    'ima-openapi-apikey': api_key,
    'ima-openapi-ctx': 'skill_version=1.1.3',
    'Content-Type': 'application/json'
}

# Prepare request body for import_doc
data = {
    'content': content,
    'content_format': 1,
    'title': 'WorkBuddy 工作记忆 - 2026-04-18'
}

# Encode data
body = json.dumps(data, ensure_ascii=False).encode('utf-8')

# Make request
url = 'https://ima.qq.com/openapi/note/v1/import_doc'
req = urllib.request.Request(url, data=body, headers=headers, method='POST')

try:
    response = urllib.request.urlopen(req)
    result = response.read().decode('utf-8')
    print('Response status:', response.status)
    print('Response body:', result)
    
    # Parse response to get doc_id
    result_json = json.loads(result)
    if result_json.get('code') == 0:
        doc_id = result_json.get('data', {}).get('doc_id')
        print(f'Successfully created note with doc_id: {doc_id}')
    else:
        print('Failed to create note:', result_json.get('msg'))
except urllib.error.HTTPError as e:
    print(f'HTTP Error: {e.code} - {e.reason}')
    error_body = e.read().decode('utf-8')
    print('Error body:', error_body)
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()