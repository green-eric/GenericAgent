#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import os

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

# Prepare headers
headers = {
    'ima-openapi-clientid': client_id,
    'ima-openapi-apikey': api_key,
    'ima-openapi-ctx': 'skill_version=1.1.3',
    'Content-Type': 'application/json'
}

# Prepare request body
data = {
    'cursor': '0',
    'limit': 10
}

# Encode data
body = json.dumps(data).encode('utf-8')

# Make request
url = 'https://ima.qq.com/openapi/note/v1/list_notebook'
req = urllib.request.Request(url, data=body, headers=headers, method='POST')

try:
    response = urllib.request.urlopen(req)
    result = response.read().decode('utf-8')
    print('Response status:', response.status)
    print('Response body:', result)
except urllib.error.HTTPError as e:
    print(f'HTTP Error: {e.code} - {e.reason}')
    error_body = e.read().decode('utf-8')
    print('Error body:', error_body)
except Exception as e:
    print(f'Error: {e}')