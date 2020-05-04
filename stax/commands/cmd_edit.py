"""
Push local state to AWS Cloudformation
"""
import collections

import click

from ..utils import class_filter, accounts_regions_and_names, set_stacks, plural


@click.command()
@accounts_regions_and_names
def edit(ctx, accounts, regions, names):
    """
    Edit locally saved stacks
    """
    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    click.echo(f'Found {plural(count, "local stack")}')

    describe_stacks = collections.defaultdict(dict)
    to_change = []

    for stack in found_stacks:
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )
        click.edit(filename=stack.template.file)
