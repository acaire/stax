"""
Click definitions common to most commands
"""
import sys

import click

from stax.aws import DEFAULT_AWS_REGIONS


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
    click.argument('names', required=False, nargs=-1),
    click.pass_context,
]


def accounts_regions_and_names(func):
    for option in _STACK_OPTIONS:
        func = option(func)
    return func