"""License API utilities for premium plugins/themes."""

import requests
import subprocess
import tempfile
import os
import zipfile
import sys
import hashlib
from . import git_utils


def check_license(api_url, license_key, plugin_basename, product_name, email, domain, instance):
    """
    Check license API for plugin/theme version.

    Args:
        api_url: License API endpoint (e.g., https://license.funnelkit.com/?wc-api=...)
        license_key: License key
        plugin_basename: Plugin basename (e.g., "funnel-builder-pro/funnel-builder-pro.php")
        product_name: Human-readable product name (e.g., "Funnel Builder Pro")
        email: License email
        domain: Site domain
        instance: Site+plugin-specific instance ID from WordPress database

    Returns:
        dict: {'version': '3.13.3', 'download_url': 'https://...'}
    """
    # Compute hash from plugin basename (WooCommerce Software Licensing API format)
    hash_key = hashlib.sha1(plugin_basename.encode()).hexdigest()

    data = {
        f'plugins[{hash_key}][plugin_slug]': plugin_basename,
        f'plugins[{hash_key}][email]': email,
        f'plugins[{hash_key}][license_key]': license_key,
        f'plugins[{hash_key}][product_id]': product_name,
        f'plugins[{hash_key}][api_key]': license_key,
        f'plugins[{hash_key}][version]': '3.7.2',
        f'plugins[{hash_key}][activation_email]': email,
        f'plugins[{hash_key}][platform]': domain,
        f'plugins[{hash_key}][domain]': domain,
        f'plugins[{hash_key}][instance]': instance,
    }

    headers = {
        'User-Agent': f'WordPress/6.4; {domain}'
    }

    # Use params instead of data for URL encoding (like curl --data-urlencode)
    response = requests.post(api_url, data=data, headers=headers, timeout=30)
    response.raise_for_status()

    result = response.json()

    # Extract from hash-keyed response
    for key, value in result.items():
        if isinstance(value, dict) and 'new_version' in value and 'package' in value:
            return {
                'version': value['new_version'],
                'download_url': value['package']
            }

    raise ValueError(f"No version info found in license API response: {result}")


def download_licensed_plugin(download_url, branch):
    """
    Download licensed plugin/theme, extract, and commit to branch.

    Args:
        download_url: Direct download URL (may be signed S3 URL)
        branch: Git branch to commit to
    """
    print(f"Downloading from {download_url[:50]}...", file=sys.stderr)

    git_utils.checkout(branch)
    git_utils.sync_locked_paths_from_master()

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        response = requests.get(download_url, timeout=120)
        response.raise_for_status()
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        # Clean current directory
        git_utils.clean_working_directory()

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

        if git_utils.has_changes():
            git_utils.commit(f"Update to version {version}")
            git_utils.create_tag(f"{branch}-v{version}")
            git_utils.push(branch)
            print(f"Committed version {version} to {branch}", file=sys.stderr)
        else:
            print(f"No changes for version {version}", file=sys.stderr)

    finally:
        os.unlink(tmp_path)
