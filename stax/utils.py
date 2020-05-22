"""
Common utilities
"""

import difflib
import json

import click
import yaml


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


def get_diff(before: any,
             after: any,
             prefix: str = "",
             fmt: str = "json") -> difflib.unified_diff:
    """
    Diff two strings
    """
    before_prefix = prefix + ' before'
    after_prefix = prefix + ' after'

    if isinstance(before, list):
        before = before.splitlines(keepends=True)
    elif isinstance(before, dict):
        if fmt == 'yaml':
            before = yaml.dump(before).splitlines(keepends=True)
        else:
            before = json.dumps(before, indent=True,
                                sort_keys=True).splitlines(keepends=True)
    elif not isinstance(before, str):
        raise ValueError(f'before {type(before)}')

    if isinstance(after, list):
        after = s2.splitlines(keepends=True)
    elif isinstance(after, dict):
        if fmt == 'yaml':
            after = yaml.dump(after).splitlines(keepends=True)
        else:
            after = json.dumps(after, indent=True,
                               sort_keys=True).splitlines(keepends=True)
    elif not isinstance(after, str):
        raise ValueError(f'after {type(after)}')

    return difflib.unified_diff(before,
                                after,
                                fromfile=before_prefix,
                                tofile=after_prefix)


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
