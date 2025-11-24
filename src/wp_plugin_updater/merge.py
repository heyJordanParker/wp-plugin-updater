"""Merge utilities for combining free and pro plugins."""

import subprocess
import tempfile
import os
import sys
from . import git_utils


def merge_branches(free_branch, pro_branch, target_branch, strategy='overlay'):
    """
    Merge free and pro branches into target branch.

    Args:
        free_branch: Branch with free plugin
        pro_branch: Branch with pro plugin
        target_branch: Branch to merge into
        strategy: Merge strategy ('overlay' = pro overlays on free)
    """
    print(f"Merging {free_branch} + {pro_branch} -> {target_branch}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as temp_dir:
        free_dir = os.path.join(temp_dir, 'free')
        pro_dir = os.path.join(temp_dir, 'pro')
        os.makedirs(free_dir)
        os.makedirs(pro_dir)

        # Copy free plugin files
        print("Copying free plugin...", file=sys.stderr)
        subprocess.run(['git', 'checkout', free_branch, '--', '.'], check=True)
        subprocess.run([
            'find', '.', '-maxdepth', '1',
            '!', '-name', '.git',
            '!', '-name', '.github',
            '!', '-name', 'scripts',
            '!', '-name', '.',
            '!', '-name', '.gitignore',
            '-exec', 'cp', '-r', '{}', free_dir + '/', ';'
        ], check=True)

        # Copy pro plugin files
        print("Copying pro plugin...", file=sys.stderr)
        subprocess.run(['git', 'checkout', pro_branch, '--', '.'], check=True)
        subprocess.run([
            'find', '.', '-maxdepth', '1',
            '!', '-name', '.git',
            '!', '-name', '.github',
            '!', '-name', 'scripts',
            '!', '-name', '.',
            '!', '-name', '.gitignore',
            '-exec', 'cp', '-r', '{}', pro_dir + '/', ';'
        ], check=True)

        git_utils.checkout(target_branch)

        # Clean target
        subprocess.run([
            'find', '.', '-maxdepth', '1',
            '!', '-name', '.git',
            '!', '-name', '.github',
            '!', '-name', 'scripts',
            '!', '-name', '.',
            '!', '-name', '.gitignore',
            '-exec', 'rm', '-rf', '{}', '+'
        ], check=True)

        # Copy free as base
        print("Merging files...", file=sys.stderr)
        subprocess.run(['cp', '-r', f"{free_dir}/.", '.'], check=True)

        # Overlay pro files
        if strategy == 'overlay':
            # Copy pro modules
            pro_modules = os.path.join(pro_dir, 'modules')
            if os.path.exists(pro_modules):
                subprocess.run(['cp', '-r', f"{pro_modules}/.", 'modules/'], check=True)

            # Copy pro main file
            for file in os.listdir(pro_dir):
                if file.endswith('-pro.php'):
                    subprocess.run(['cp', os.path.join(pro_dir, file), '.'], check=True)

            # Copy pro-specific files (except license.txt which exists in free)
            for file in ['changelog.txt', 'loco.xml']:
                src = os.path.join(pro_dir, file)
                if os.path.exists(src):
                    subprocess.run(['cp', src, '.'], check=True)

        # Get versions for commit message
        free_version = _get_version_from_branch(free_branch)
        pro_version = _get_version_from_branch(pro_branch)

        if git_utils.has_changes():
            git_utils.commit(f"Merge Free v{free_version} and Pro v{pro_version}")
            git_utils.create_tag(f"funnelkit-v{free_version}-v{pro_version}")
            git_utils.push(target_branch)
            print(f"Merged and committed to {target_branch}", file=sys.stderr)
        else:
            print("No changes after merge", file=sys.stderr)


def _get_version_from_branch(branch):
    """Get version from a branch's plugin file."""
    # Get latest tag for branch
    result = subprocess.run(
        ['git', 'describe', '--tags', '--abbrev=0', branch],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        tag = result.stdout.strip()
        # Extract version from tag (e.g., "free-v3.13.1.3" -> "3.13.1.3")
        if '-v' in tag:
            return tag.split('-v')[1]
    return "unknown"
