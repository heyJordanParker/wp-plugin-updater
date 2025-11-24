"""License API utilities for premium plugins/themes."""

import requests
import subprocess
import tempfile
import os
import zipfile
import sys


def check_license(api_url, license_key, product_id, email):
    """
    Check license API for plugin/theme version.

    Args:
        api_url: License API endpoint
        license_key: License key
        product_id: Product identifier
        email: License email

    Returns:
        dict: {'version': '3.13.3', 'download_url': 'https://...'}
    """
    # Build request data for FunnelKit-style API
    data = {
        'plugins[ffec4bb68f0841db41213ce12305aaef7e0237f3][plugin_slug]': f"{product_id}/{product_id}.php",
        'plugins[ffec4bb68f0841db41213ce12305aaef7e0237f3][email]': email,
        'plugins[ffec4bb68f0841db41213ce12305aaef7e0237f3][license_key]': license_key,
        'plugins[ffec4bb68f0841db41213ce12305aaef7e0237f3][product_id]': product_id,
        'plugins[ffec4bb68f0841db41213ce12305aaef7e0237f3][api_key]': license_key,
        'plugins[ffec4bb68f0841db41213ce12305aaef7e0237f3][version]': '1.0.0',
        'plugins[ffec4bb68f0841db41213ce12305aaef7e0237f3][activation_email]': email,
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'WordPress/6.4; https://example.com'
    }

    response = requests.post(api_url, data=data, headers=headers, timeout=30)
    response.raise_for_status()

    result = response.json()

    # Extract from first key (hash-based response)
    for key, value in result.items():
        if isinstance(value, dict) and 'new_version' in value:
            return {
                'version': value['new_version'],
                'download_url': value['package']
            }

    raise ValueError("No version info found in license API response")


def download_licensed_plugin(download_url, branch):
    """
    Download licensed plugin/theme, extract, and commit to branch.

    Args:
        download_url: Direct download URL (may be signed S3 URL)
        branch: Git branch to commit to
    """
    print(f"Downloading from {download_url[:50]}...", file=sys.stderr)

    # Switch to branch
    subprocess.run(['git', 'checkout', branch], check=True)

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        response = requests.get(download_url, timeout=120)
        response.raise_for_status()
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        # Clean current directory (preserve git, scripts, etc.)
        subprocess.run([
            'find', '.', '-maxdepth', '1',
            '!', '-name', '.git',
            '!', '-name', '.github',
            '!', '-name', 'scripts',
            '!', '-name', '.',
            '!', '-name', '.gitignore',
            '-exec', 'rm', '-rf', '{}', '+'
        ], check=True)

        # Extract plugin
        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            with tempfile.TemporaryDirectory() as extract_dir:
                zip_ref.extractall(extract_dir)

                # Find plugin directory
                dirs = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
                if not dirs:
                    raise ValueError("No plugin directory found in archive")

                plugin_dir = os.path.join(extract_dir, dirs[0])

                # Copy files to current directory
                subprocess.run(['cp', '-r', f"{plugin_dir}/.", '.'], check=True)

        # Get version from main plugin file
        php_files = [f for f in os.listdir('.') if f.endswith('.php') and os.path.isfile(f)]
        version = None
        for php_file in php_files:
            with open(php_file, 'r') as f:
                for line in f:
                    if 'Version:' in line:
                        version = line.split('Version:')[1].strip()
                        break
                if version:
                    break

        if not version:
            version = "unknown"

        # Check for changes
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout.strip():
            subprocess.run(['git', 'add', '-A'], check=True)
            subprocess.run(['git', 'commit', '-m', f"Update to version {version}"], check=True)
            subprocess.run(['git', 'tag', f"pro-v{version}"], check=True)
            subprocess.run(['git', 'push', 'origin', branch, '--tags'], check=True)
            print(f"Committed version {version} to {branch}")
        else:
            print(f"No changes for version {version}")

    finally:
        os.unlink(tmp_path)
