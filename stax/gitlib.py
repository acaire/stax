"""
Git Helpers
"""

import os
import git
import subprocess, shlex

REPO = git.Repo(os.getcwd(), search_parent_directories=True)


def current_branch():
    """
    Return the current branch
    """
    return f'{REPO.active_branch}'


def lookup_sha(revision=REPO.active_branch):
    """
    Return the current branch
    """
    return REPO.git.rev_parse(REPO.active_branch, short=True)


def commits_between_old(rev1, rev2='origin/master'):
    """
    Count the commits between two references
    """
    return subprocess.check_output(
        shlex.split(f"git rev-list --count {rev1}..{rev2}")).strip().decode(
            'utf-8')


def commits_between(rev1, rev2='origin/master'):
    """
    Return the number of commits between two references
    Optionally return just the count
    """
    return len([REPO.iter_commits(f'{rev1}..{rev2}')])


def user_email():
    """
    Return the git user
    """
    return REPO.config_reader().get_value('user', 'email')


def file_contents(filename, revision):
    """
    Return the contents of a file from a specific revision
    """
    return REPO.git.show(f'{revision}:{filename}')


def changed_files(revision="HEAD^1"):
    """
    Return changed files since the last commit
    """
    return REPO.git.diff(f'{revision}', name_only=True).split('\n')
