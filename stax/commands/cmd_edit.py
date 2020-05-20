"""
Edit a locally defined Cloudformation stack
"""
import click

from stax.commands.common import accounts_regions_and_names, class_filter
from stax.stack import Cloudformation, load_stacks
from stax.utils import plural


@click.command()
@accounts_regions_and_names
def edit(ctx, accounts, regions, names):
    """
    Edit locally saved stacks
    """
    load_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    click.echo(f'Found {plural(count, "local stack")} to edit')

    for stack in found_stacks:
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )
        click.edit(filename=stack.template.filename)
        if stack.params.filename:
            click.edit(filename=stack.params.filename)
