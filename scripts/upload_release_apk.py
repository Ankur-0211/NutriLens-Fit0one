import json
import os
import sys
import urllib.request
import urllib.error

import subprocess

TOKEN = os.environ.get('GITHUB_TOKEN')
if not TOKEN:
    try:
        proc = subprocess.run(['git', 'credential', 'fill'], input=b'protocol=https\nhost=github.com\n\n', capture_output=True)
        for line in proc.stdout.decode().splitlines():
            if line.startswith('password='):
                TOKEN = line.split('=', 1)[1]
    except Exception:
        pass
REPO = 'Ankur-0211/NutriLens-Fit0one'
RELEASE_ID = 402838078
APK_PATH = os.path.abspath('nutrilens.apk')

def get_release():
    url = f"https://api.github.com/repos/{REPO}/releases/{RELEASE_ID}"
    req = urllib.request.Request(url, headers={
        'Authorization': f'token {TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'NutriLens-Uploader'
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def delete_asset(asset_id, name):
    print(f"Deleting old asset {name} (ID: {asset_id})...")
    url = f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}"
    req = urllib.request.Request(url, method='DELETE', headers={
        'Authorization': f'token {TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'NutriLens-Uploader'
    })
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Successfully deleted {name}: status {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError deleting {name}: {e.code} {e.read().decode('utf-8')}")

def upload_asset(file_path, asset_name):
    file_size = os.path.getsize(file_path)
    print(f"Uploading {asset_name} ({file_size} bytes / {file_size / (1024*1024):.2f} MB)...")
    url = f"https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets?name={asset_name}"
    
    with open(file_path, 'rb') as f:
        file_data = f.read()

    req = urllib.request.Request(url, data=file_data, method='POST', headers={
        'Authorization': f'token {TOKEN}',
        'Content-Type': 'application/vnd.android.package-archive',
        'Content-Length': str(file_size),
        'User-Agent': 'NutriLens-Uploader'
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"Uploaded successfully! Asset ID: {data.get('id')}, URL: {data.get('browser_download_url')}")
            return data
    except urllib.error.HTTPError as e:
        print(f"Upload failed: {e.code} - {e.read().decode('utf-8')}")
        raise

if __name__ == '__main__':
    release = get_release()
    print(f"Release Tag: {release.get('tag_name')}, Name: {release.get('name')}")
    
    # 1. Delete existing assets with target names
    for asset in release.get('assets', []):
        if asset['name'] in ['nutrilens.apk', 'app-release.apk']:
            delete_asset(asset['id'], asset['name'])
            
    # 2. Upload new nutrilens.apk and app-release.apk
    upload_asset(APK_PATH, 'nutrilens.apk')
    upload_asset(APK_PATH, 'app-release.apk')
    print("ALL ASSETS SUCCESSFULLY UPLOADED!")
