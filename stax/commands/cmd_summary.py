"""
Summary
"""
import collections

import click

from ..utils import class_filter, accounts_regions_and_names, set_stacks, plural


@click.command()
@accounts_regions_and_names
def summary(ctx, accounts, regions, names):
    """
    Show stax.json summary
    """
    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    accounts = collections.Counter()

    for stack in found_stacks:
        accounts[stack.account] += 1

    click.echo('Account,StackCount')
    for account, stack_count in accounts.most_common():
        click.echo(f'{account},{stack_count}')
