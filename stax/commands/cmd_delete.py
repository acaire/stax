"""
Push local state to AWS Cloudformation
"""
import click

from ..exceptions import StaxException
from ..utils import class_filter, stack_options, set_stacks, plural


@click.command()
@stack_options
def delete(ctx, accounts, regions, name):
    """
    Delete live stacks
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
