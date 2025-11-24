"""WordPress.org plugin utilities."""

import requests
import subprocess
import tempfile
import os
import zipfile
import sys
from . import git_utils


def check_wordpress_org(slug):
    """
    Check WordPress.org for plugin version.

    Args:
        slug: Plugin slug (e.g., 'funnel-builder')

    Returns:
        dict: {'version': '3.13.1.3', 'download_url': 'https://...'}
    """
    url = f"https://api.wordpress.org/plugins/info/1.0/{slug}.json"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    version = data.get('version')

    if not version:
        raise ValueError(f"No version found for plugin: {slug}")

    download_url = f"https://downloads.wordpress.org/plugin/{slug}.{version}.zip"

    return {
        'version': version,
        'download_url': download_url
    }


def download_wordpress_plugin(slug, version, branch):
    """
    Download WordPress.org plugin, extract, and commit to branch.

    Args:
        slug: Plugin slug
        version: Version to download
        branch: Git branch to commit to
    """
    download_url = f"https://downloads.wordpress.org/plugin/{slug}.{version}.zip"

    print(f"Downloading {slug} v{version}...", file=sys.stderr)

    git_utils.checkout(branch)

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        response = requests.get(download_url, timeout=60)
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
            # Extract to temp dir first
            with tempfile.TemporaryDirectory() as extract_dir:
                zip_ref.extractall(extract_dir)

                # Find plugin directory (usually just the slug)
                plugin_dir = os.path.join(extract_dir, slug)
                if not os.path.exists(plugin_dir):
                    # Try finding any directory
                    dirs = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
                    if dirs:
                        plugin_dir = os.path.join(extract_dir, dirs[0])
                    else:
                        raise ValueError("No plugin directory found in archive")

                # Copy files to current directory
                subprocess.run(['cp', '-r', f"{plugin_dir}/.", '.'], check=True)

        if git_utils.has_changes():
            git_utils.commit(f"Update {slug} to version {version}")
            git_utils.create_tag(f"{branch}-v{version}")
            git_utils.push(branch)
            print(f"Committed {slug} v{version} to {branch}", file=sys.stderr)
        else:
            print(f"No changes for {slug} v{version}", file=sys.stderr)

    finally:
        os.unlink(tmp_path)
