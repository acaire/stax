"""
Push local state to AWS Cloudformation
"""
import click

from ..exceptions import StackNotFound
from ..utils import class_filter, stack_options, set_stacks, plural


@click.command()
@stack_options
def push(ctx, accounts, regions, name):
    """
    Create/Update live stacks
    """

    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=name)

    click.echo(f'Found {plural(count, "local stack")} to push')

    for stack in found_stacks:
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )
        try:
            # Update should be common than create
            stack.update()
        except StackNotFound:
            stack.create()
