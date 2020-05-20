"""
Peer into the outputs and resources of a Cloudformation stack
"""
import textwrap

import click

from stax.commands.common import accounts_regions_and_names, class_filter
from stax.stack import Cloudformation, load_stacks
from stax.utils import plural


@click.command()
@accounts_regions_and_names
def peer(ctx, accounts, regions, names):
    """
    Peer into the outputs and resources of a stack
    """
    load_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    click.echo(f'Found {plural(count, "local stack")} to peer into\n')

    for stack in sorted(found_stacks, key=lambda x: x.name):
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )
        click.secho(click.style('Outputs', bold=True))

        stack_dict = stack.template.to_dict

        click.secho(click.style('Resources', bold=True), nl='')
        for resource in stack.resources:
            click.echo(
                textwrap.dedent(f'''
                 logical resource id: {resource["LogicalResourceId"]}
                physical resource id: {resource["PhysicalResourceId"]}
                     resource status: {resource["ResourceStatus"]}
                       status reason: {resource.get("ResourceStatusReason", "")}'''
                                ))
