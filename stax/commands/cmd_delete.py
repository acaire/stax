"""
Delete a single named Cloudformation stack
"""
import click

from stax.commands.common import accounts_regions_and_names, class_filter
from stax.exceptions import StackNotFound
from stax.stack import Cloudformation, load_stacks
from stax.utils import plural


@click.command()
@accounts_regions_and_names
@click.argument('name', required=True)
def delete(ctx, accounts, regions, name):
    """
    Delete a single live stack
    """
    load_stacks(ctx)
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
        except StackNotFound as err:
            click.echo(err)
