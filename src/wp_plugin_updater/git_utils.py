"""Git utilities for plugin update operations."""

import os
import subprocess


DEFAULT_LOCKED_PATHS = ['.git', '.github', '.gitignore']


def reset():
    """
    Reset working directory to HEAD.
    """
    subprocess.run(['git', 'reset', '--hard'], check=True)


def checkout(branch, auto_reset=True):
    """
    Checkout branch, tracking remote if exists, otherwise create new.

    Args:
        branch: Branch name to checkout
        auto_reset: Reset working directory before checkout (default: True)
    """
    if auto_reset:
        reset()

    subprocess.run(['git', 'fetch', 'origin'], capture_output=True)
    result = subprocess.run(['git', 'checkout', branch], capture_output=True)
    if result.returncode != 0:
        # Check if remote branch exists
        remote_check = subprocess.run(
            ['git', 'ls-remote', '--heads', 'origin', branch],
            capture_output=True,
            text=True
        )
        if remote_check.stdout.strip():
            subprocess.run(['git', 'checkout', '-b', branch, f'origin/{branch}'], check=True)
        else:
            subprocess.run(['git', 'checkout', '-b', branch], check=True)


def create_tag(tag):
    """
    Create tag if it doesn't exist.

    Args:
        tag: Tag name to create
    """
    tag_check = subprocess.run(['git', 'tag', '-l', tag], capture_output=True, text=True)
    if not tag_check.stdout.strip():
        subprocess.run(['git', 'tag', tag], check=True)


def commit(message):
    """
    Stage all changes and commit.

    Args:
        message: Commit message
    """
    subprocess.run(['git', 'add', '-A'], check=True)
    subprocess.run(['git', 'commit', '-q', '-m', message], check=True)


def push(branch):
    """
    Push branch and tags to origin.

    Args:
        branch: Branch name to push
    """
    subprocess.run(['git', 'push', '-q', 'origin', branch, '--tags'], check=True)


def has_changes():
    """
    Check if there are uncommitted changes.

    Returns:
        bool: True if there are changes
    """
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    return bool(result.stdout.strip())


def get_locked_paths():
    """
    Get locked paths from defaults + LOCKED_PATHS env var.

    Returns:
        list: List of paths to preserve during operations
    """
    locked_paths = DEFAULT_LOCKED_PATHS.copy()
    env_paths = os.environ.get('LOCKED_PATHS', '').strip()
    if env_paths:
        locked_paths.extend(env_paths.split(','))
    return locked_paths


def sync_locked_paths_from_master():
    """
    Hard reset locked paths from master branch.

    Fetches master and checks out locked paths from it,
    then commits if there are changes.
    """
    locked_paths = get_locked_paths()
    subprocess.run(['git', 'fetch', 'origin', 'master:refs/remotes/origin/master'], check=True)

    for path in locked_paths:
        if path == '.git':  # Skip .git itself - can't checkout
            continue
        # Check if path exists in origin/master before trying to checkout
        check_result = subprocess.run(
            ['git', 'cat-file', '-e', f'origin/master:{path}'],
            capture_output=True
        )
        if check_result.returncode == 0:
            subprocess.run(['git', 'checkout', 'origin/master', '--', path], check=True)

    if has_changes():
        commit("Sync locked paths from master")


def clean_working_directory():
    """
    Remove all files except locked paths.

    Preserves paths from get_locked_paths() and the current directory.
    Used when downloading plugins to ensure clean state.
    """
    locked_paths = get_locked_paths()
    exclude_args = ['!', '-name', '.']
    for path in locked_paths:
        exclude_args.extend(['!', '-name', path])

    subprocess.run(
        ['find', '.', '-maxdepth', '1'] + exclude_args + ['-exec', 'rm', '-rf', '{}', '+'],
        check=True
    )
