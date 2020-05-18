"""
Print a summary of locally defined Cloudformation stacks
"""
import collections

import click

from stax.commands.common import accounts_regions_and_names, class_filter
from stax.stack import Cloudformation, load_stacks
from stax.utils import plural


@click.command()
@accounts_regions_and_names
def summary(ctx, accounts, regions, names):
    """
    Show stax.json summary
    """
    load_stacks(ctx)
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
