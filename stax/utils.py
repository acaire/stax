import collections
import os
import sys

import click

from . import gitlib
from .aws.cloudformation import Stack, DEFAULT_AWS_REGIONS


def default_tags(ctx):
    """
    Return some default tags based on chosen CI
    """
    if ctx.obj.config.get('ci') == 'buildkite':
        return {
            "BUILDKITE_COMMIT":
            os.getenv("BUILDKITE_COMMIT", gitlib.current_branch()),
            "BUILDKITE_BUILD_URL":
            os.getenv("BUILDKITE_BUILD_URL", "dev"),
            "BUILDKITE_REPO":
            os.getenv("BUILDKITE_REPO", "dev"),
            "BUILDKITE_BUILD_CREATOR":
            os.getenv("BUILDKITE_BUILD_CREATOR", gitlib.user_email()),
        }
    return {}


def default_accounts(ctx, param, value):
    """
    Assemble the names of defined accounts
    to be used as CLI defaults
    """
    try:
        accounts = [acc for acc in ctx.obj.config['accounts']]
    except KeyError:
        sys.exit('Error: No accounts configured in stax.json')

    if value:
        result = [acc for acc in value if acc in accounts]
    else:
        result = accounts

    if len(result) < 1:
        sys.exit('No matching accounts found in stax.json')

    return result


def class_filter(instances, **filters):
    """
    Search for class instances by their attributes
    """
    found_instances = []
    for instance in instances:
        for filter_key, filter_value in filters.items():
            if not filter_value:
                continue
            looking_for = getattr(instance, filter_key)
            if isinstance(filter_value, str):
                if looking_for != filter_value:
                    break
            else:
                if looking_for not in filter_value:
                    break
        else:
            found_instances.append(instance)

    return len(found_instances), found_instances


_STACK_OPTIONS = [
    click.option('--account',
                 '-a',
                 'accounts',
                 multiple=True,
                 callback=default_accounts),
    click.option('--region',
                 '-r',
                 'regions',
                 type=click.Choice(DEFAULT_AWS_REGIONS),
                 multiple=True,
                 default=DEFAULT_AWS_REGIONS),
    click.argument('name', required=False),
    click.pass_context,
]


def stack_options(func):
    for option in _STACK_OPTIONS:
        func = option(func)
    return func


def set_stacks(ctx):
    ctx.obj.stacks = collections.defaultdict(dict)

    ctx.obj.stacks = [
        Stack(name=name,
              account=account,
              region=region,
              params=params_file if params_file else None,
              template_file=stack['template'],
              tags=default_tags(ctx))
        for name, stack in ctx.obj.config['stacks'].items() for region in
        stack.get('regions',
                  [ctx.obj.config.get('default_region', 'ap-southeast-2')])
        for account, params_file in stack['parameters'].items()
    ]


def plural(count, singular, plural=None):
    if count == 1:
        return f'{count} {singular}'
    else:
        if plural:
            return f'{count} {plural}'
        return f'{count} {singular}s'
