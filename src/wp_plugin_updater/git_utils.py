"""Git utilities for plugin update operations."""

import subprocess


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


def clean_working_directory():
    """
    Remove all files except git infrastructure.

    Preserves only .git, .gitignore, and the current directory.
    Used when downloading plugins to ensure clean state.
    """
    subprocess.run([
        'find', '.', '-maxdepth', '1',
        '!', '-name', '.git',
        '!', '-name', '.',
        '!', '-name', '.gitignore',
        '-exec', 'rm', '-rf', '{}', '+'
    ], check=True)
