"""
Common utilities
"""

import difflib

import click


def plural(count: int, singular: str, plural: str = "") -> str:
    """
    Pluralise a word based on provided count
    """
    if count == 1:
        return f'{count} {singular}'
    else:
        if plural:
            return f'{count} {plural}'
        else:
            return f'{count} {singular}s'


def get_diff(s1: str, s2: str, prefix: str = "") -> difflib.unified_diff:
    """
    Diff two strings
    """
    before = prefix + ' before'
    after = prefix + ' after'
    if isinstance(s1, str):
        s1 = s1.splitlines(keepends=True)
    if isinstance(s2, str):
        s2 = s2.splitlines(keepends=True)

    return difflib.unified_diff(s1, s2, fromfile=before, tofile=after)


def print_diff(diff: difflib.unified_diff) -> int:
    """
    Print a unified diff, and return a count of changes
    """
    changes = 0

    for line in diff:
        if line.startswith('+'):
            click.secho(line, fg='green', nl=False)
            changes += 1
        elif line.startswith('-'):
            click.secho(line, fg='red', nl=False)
            changes += 1
        else:
            click.echo(line, nl=False)
    if changes:
        click.echo('\n')
    return changes


def list_to_dict(the_list, k, v):
    """
    Return a list of dictionaries
    """
    return {l[k]: l[v] for l in the_list}


def dict_to_list(the_dict, key, value):
    """
    Return a dict of list items
    """
    return [{key: k, value: v} for k, v in the_dict.items()]
