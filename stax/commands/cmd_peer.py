"""
Peer into the outputs and resources of a stack
"""
import collections

import click
import halo

from ..utils import (accounts_regions_and_names, class_filter, plural,
                     set_stacks)


@click.command()
@accounts_regions_and_names
def peer(ctx, accounts, regions, names):
    """
    Peer into the outputs and resources of a stack
    """
    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    click.echo(f'Found {plural(count, "local stack")}\n')

    describe_stacks = collections.defaultdict(dict)
    to_change = []

    for stack in sorted(found_stacks, key=lambda x: x.name):
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )
        click.secho(click.style('Outputs', bold=True))

        stack_dict = stack.template.to_dict

        print(stack_dict['Outputs'] if stack.template.
              to_dict['Outputs'] else None)

        for resource in stack.resources:
            print(resource['LogicalResourceId'],
                  resource['PhysicalResourceId'], resource['ResourceStatus'],
                  resource.get('ResourceStatusReason', ''))
