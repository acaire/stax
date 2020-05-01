"""
Push local state to AWS Cloudformation
"""
import collections
import sys

import click
import halo

from ..aws.cloudformation import Cloudformation
from ..exceptions import StackNotFound
from ..utils import class_filter, stack_options, set_stacks, plural


@click.command()
@stack_options
@click.option('--force', is_flag=True)
@click.option('--use-existing-params', is_flag=True)
@click.option('--skip-tags', is_flag=True)
def push(ctx, accounts, regions, name, force, use_existing_params, skip_tags):
    """
    Create/Update live stacks
    """
    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=name)

    click.echo(f'Found {plural(count, "local stack")}')

    describe_stacks = collections.defaultdict(dict)
    to_change = []

    for stack in found_stacks:
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )

        # If we have a small number of stacks, it's faster to just create changesets
        if (len(found_stacks) < 20 or name or force or stack.purge):
            if stack.purge:
                ctx.obj.debug(f'Checking to see if {stack.name} still exists')
                if not stack.exists:
                    continue
            to_change.append(stack)
        # Use describe stacks and compare STAX_HASH tag
        else:
            key = f'{stack.account},{stack.region}'
            if key not in describe_stacks:
                cf = Cloudformation(account=stack.account, region=stack.region)
                with halo.Halo('Fetching stack status'):
                    describe_stacks[key] = cf.describe_stacks()
            try:
                stax_hash = [
                    tag['Value']
                    for tag in describe_stacks[key][stack.name]['Tags']
                    if tag['Key'] == 'STAX_HASH'
                ][0]
            except (KeyError, IndexError):
                stax_hash = None
            if stack.pending_update(stax_hash):
                to_change.append(stack)
    if not found_stacks:
        click.echo('No stacks found to update')
        sys.exit(1)

    print('{} to update... {}\n'.format(
        plural(len(to_change), 'stack'),
        [stack.name for stack in to_change] if to_change else ''))
    # Update should be more common than create, so let's assume that and save time
    for stack in to_change:
        if stack.purge is False:
            try:
                stack.update(use_existing_params=use_existing_params,
                             skip_tags=skip_tags)
            except StackNotFound:
                stack.create()
            else:
                ctx.obj.debug(f'No change required for {stack.name}')
        else:
            if stack.exists:
                stack.delete()
