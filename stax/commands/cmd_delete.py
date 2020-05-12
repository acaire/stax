"""
Push local state to AWS Cloudformation
"""
import click

from ..exceptions import StaxException
from ..utils import (accounts_regions_and_names, class_filter, plural,
                     set_stacks)


@click.command()
@accounts_regions_and_names
@click.argument('name', required=True)
def delete(ctx, accounts, regions, name):
    """
    Delete a single live stack
    """
    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=name)

    click.echo(f'Found {plural(count, "local stack")} to delete')

    for stack in found_stacks:
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )
        try:
            stack.delete()
        except StaxException.StackNotFound as err:
            print(err)
