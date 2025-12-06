"""Version comparison utilities for WordPress plugins."""

import os
import re
import subprocess
from packaging.version import Version, InvalidVersion


def extract_from_php_header(directory="."):
    """
    Extract version from WordPress plugin/theme PHP header.

    Args:
        directory: Directory containing PHP files (default: current directory)

    Returns:
        str: Version string or None if not found
    """
    php_files = [f for f in os.listdir(directory) if f.endswith('.php') and os.path.isfile(os.path.join(directory, f))]

    for php_file in php_files:
        filepath = os.path.join(directory, php_file)
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if 'Version:' in line:
                    return line.split('Version:')[1].strip()

    return None


def extract_from_branch(branch):
    """
    Extract version from a git branch's PHP header.

    Args:
        branch: Git branch name

    Returns:
        str: Version string or None if not found
    """
    result = subprocess.run(
        ['git', 'ls-tree', '-r', '--name-only', branch],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        return None

    output = result.stdout.strip()
    if not output:
        return None

    # Filter for root-level PHP files only (no subdirectories)
    php_files = [f for f in output.split('\n') if f.endswith('.php') and '/' not in f]

    for php_file in php_files:
        content = subprocess.run(
            ['git', 'show', f'{branch}:{php_file}'],
            capture_output=True, text=True
        )
        if content.returncode == 0:
            for line in content.stdout.split('\n'):
                if 'Version:' in line:
                    return line.split('Version:')[1].strip()

    return None


def is_newer(candidate, current):
    """
    Check if candidate version is newer than current version.

    Uses PEP 440 semver comparison which handles alpha/beta/rc correctly:
    - 4.0.0-alpha < 4.0.0
    - 3.3.6 < 4.0.0-alpha

    Args:
        candidate: Version string to check (e.g., "3.3.7")
        current: Current version string (e.g., "4.0.0-alpha")

    Returns:
        bool: True if candidate > current
    """
    if not candidate or not current:
        return candidate is not None

    try:
        candidate_normalized = _normalize(candidate)
        current_normalized = _normalize(current)
        return Version(candidate_normalized) > Version(current_normalized)
    except InvalidVersion:
        # Extract base version numbers for comparison when format is non-standard
        candidate_base = re.match(r'^[\d.]+', candidate)
        current_base = re.match(r'^[\d.]+', current)
        if candidate_base and current_base:
            try:
                return Version(candidate_base.group()) > Version(current_base.group())
            except InvalidVersion:
                pass
        return candidate != current


def _normalize(version):
    """
    Normalize version string to PEP 440 format.

    Converts WordPress-style versions to Python packaging format:
    - "4.0.0-alpha" -> "4.0.0a0"
    - "4.0.0-beta.2" -> "4.0.0b2"
    - "4.0.0-rc.1" -> "4.0.0rc1"

    Args:
        version: Raw version string

    Returns:
        str: PEP 440 compliant version string
    """
    version = version.lower().strip()

    version = re.sub(r'-alpha\.?(\d*)', lambda m: f'a{m.group(1) or 0}', version)
    version = re.sub(r'-beta\.?(\d*)', lambda m: f'b{m.group(1) or 0}', version)
    version = re.sub(r'-rc\.?(\d*)', lambda m: f'rc{m.group(1) or 0}', version)

    return version
