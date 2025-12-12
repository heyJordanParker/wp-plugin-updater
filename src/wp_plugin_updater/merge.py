"""Merge utilities for combining plugin branches."""

import subprocess
import tempfile
import os
import re
import sys
from . import git_utils


def merge(branches, target=None, strategy='overlay', push=True):
    """
    Merge multiple branches into target branch or working directory.

    Args:
        branches: List of branches to merge (first=base, rest overlay on top)
        target: Branch to merge into (None=stay on current branch)
        strategy: How to overlay files ('overlay'=later overwrites earlier)
        push: Commit and push result (False=leave uncommitted in working directory)
    """
    if len(branches) < 2:
        raise ValueError("Need at least 2 branches to merge")

    print(f"Merging {' + '.join(branches)}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy each branch to temp directory
        branch_dirs = []
        for i, branch in enumerate(branches):
            branch_dir = os.path.join(temp_dir, f'branch{i}')
            os.makedirs(branch_dir)

            print(f"Copying {branch}...", file=sys.stderr)
            # Use git archive to extract clean branch content without working dir pollution
            archive = subprocess.run(
                ['git', 'archive', '--format=tar', branch],
                capture_output=True,
                check=True
            )
            # Exclude .github and .gitignore (these come from target branch only)
            subprocess.run(
                ['tar', '-xf', '-', '-C', branch_dir, '--exclude=.github', '--exclude=.gitignore'],
                input=archive.stdout,
                check=True
            )

            branch_dirs.append(branch_dir)

        # Checkout target branch if specified
        if target:
            git_utils.checkout(target)

        # Clean working directory
        git_utils.clean_working_directory()

        # Apply branches in order
        print("Merging files...", file=sys.stderr)

        # First branch is base
        subprocess.run(['cp', '-r', f"{branch_dirs[0]}/.", '.'], check=True)

        # Overlay remaining branches
        if strategy == 'overlay':
            for i in range(1, len(branch_dirs)):
                branch_dir = branch_dirs[i]

                # Find main plugin file to determine plugin name
                main_plugin = _find_main_plugin_file(branch_dir)
                if main_plugin:
                    plugin_name = main_plugin[:-4]  # Remove .php
                    print(f"Relocating {plugin_name} to subdirectory...", file=sys.stderr)

                    # Copy entire branch into subdirectory
                    subdir = plugin_name
                    os.makedirs(subdir, exist_ok=True)
                    for entry in os.listdir(branch_dir):
                        src = os.path.join(branch_dir, entry)
                        subprocess.run(['cp', '-r', src, f'{subdir}/'], check=True)

                    # Extract headers from main plugin and generate stub with headers
                    main_plugin_path = os.path.join(branch_dir, main_plugin)
                    headers = _extract_plugin_headers(main_plugin_path)
                    stub_content = _generate_stub_with_headers(headers, subdir, main_plugin)
                    with open(f'{plugin_name}.php', 'w') as f:
                        f.write(stub_content)
                    print(f"Created loader: {plugin_name}.php (with {len(headers)} headers)", file=sys.stderr)
                else:
                    # Fallback: old behavior for branches without clear main plugin
                    # Copy modules directory if exists
                    modules_dir = os.path.join(branch_dir, 'modules')
                    if os.path.exists(modules_dir):
                        if os.path.exists('modules'):
                            subprocess.run(['cp', '-r', f"{modules_dir}/.", 'modules/'], check=True)
                        else:
                            subprocess.run(['cp', '-r', modules_dir, '.'], check=True)

                    # Copy main plugin files (PHP files in root)
                    for file in os.listdir(branch_dir):
                        file_path = os.path.join(branch_dir, file)
                        if os.path.isfile(file_path) and file.endswith('.php'):
                            subprocess.run(['cp', file_path, '.'], check=True)

                    # Copy other specific files
                    for file in ['changelog.txt', 'loco.xml']:
                        src = os.path.join(branch_dir, file)
                        if os.path.exists(src):
                            subprocess.run(['cp', src, '.'], check=True)

        # Get versions for commit message
        versions = []
        for i, branch in enumerate(branches):
            version = _get_version_from_branch(branch)
            versions.append(f"{branch}={version}")

        # Commit and push if requested
        if push and git_utils.has_changes():
            version_str = ", ".join(versions)
            git_utils.commit(f"Merge {version_str}")
            git_utils.create_tag(f"merged-{'-'.join([v.split('=')[1] for v in versions])}")
            git_utils.push(target if target else 'HEAD')
            print(f"Merged and pushed", file=sys.stderr)
        elif git_utils.has_changes():
            print(f"Merged to working directory (uncommitted)", file=sys.stderr)
        else:
            print("No changes after merge", file=sys.stderr)


def _find_main_plugin_file(branch_dir):
    """Find the main plugin PHP file in a branch directory.

    Looks for a PHP file with 'Plugin Name:' header, excluding index.php.
    Returns filename (e.g., 'fluent-community-pro.php') or None.
    """
    for file in os.listdir(branch_dir):
        if not file.endswith('.php') or file == 'index.php':
            continue
        file_path = os.path.join(branch_dir, file)
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2048)  # First 2KB should contain header
                if 'Plugin Name:' in content:
                    return file
        except:
            continue
    return None


def _extract_plugin_headers(file_path):
    """Extract WordPress plugin headers from a PHP file.

    Handles common formats:
    - Docblock: /** * Plugin Name: Foo */
    - Simple:   /* Plugin Name: Foo */
    - Mixed:    /* * Plugin Name: Foo */

    Returns dict with header keys (e.g., 'Plugin Name', 'Version', 'Author').
    """
    headers = {}
    header_keys = [
        'Plugin Name', 'Plugin URI', 'Description', 'Version',
        'Author', 'Author URI', 'License', 'License URI',
        'Text Domain', 'Domain Path', 'Network', 'Requires at least',
        'Requires PHP', 'Update URI'
    ]

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(8192)  # Headers should be in first 8KB
    except:
        return headers

    for key in header_keys:
        # Match "Key: Value" - value extends to end of line
        # Handles: "Plugin Name: Foo", " * Plugin Name: Foo", etc.
        pattern = rf'^\s*\*?\s*{re.escape(key)}\s*:\s*(.+?)$'
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            # Clean up trailing comment artifacts (*, */, whitespace)
            value = re.sub(r'\s*\*+/?$', '', value).strip()
            if value:
                headers[key] = value

    return headers


def _generate_stub_with_headers(headers, subdir, main_plugin):
    """Generate a stub PHP file with WordPress plugin headers.

    Returns the complete PHP content for the stub file.
    """
    lines = ['<?php', '/**']

    # Standard header order
    header_order = [
        'Plugin Name', 'Plugin URI', 'Description', 'Version',
        'Author', 'Author URI', 'License', 'License URI',
        'Text Domain', 'Domain Path', 'Network', 'Requires at least',
        'Requires PHP', 'Update URI'
    ]

    for key in header_order:
        if key in headers:
            value = headers[key]
            # Adjust Domain Path to account for subdirectory relocation
            if key == 'Domain Path' and value.startswith('/'):
                value = f'/{subdir}{value}'
            lines.append(f' * {key}: {value}')

    lines.append(' */')
    lines.append(f"require_once __DIR__ . '/{subdir}/{main_plugin}';")
    lines.append('')  # Trailing newline

    return '\n'.join(lines)


def _get_version_from_branch(branch):
    """Get version from a branch's latest tag."""
    result = subprocess.run(
        ['git', 'describe', '--tags', '--abbrev=0', branch],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        tag = result.stdout.strip()
        # Extract version from tag (e.g., "plugin-v3.13.1.3" -> "3.13.1.3")
        if '-v' in tag:
            return tag.split('-v')[-1]
        return tag.replace('v', '')
    return "unknown"
