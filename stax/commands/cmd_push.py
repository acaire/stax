"""
Push local state to AWS Cloudformation
"""
import collections
import sys

import click
import halo

from stax.commands.common import accounts_regions_and_names, class_filter
from stax.exceptions import StackNotFound
from stax.stack import Cloudformation, load_stacks
from stax.utils import plural


@click.command()
@accounts_regions_and_names
@click.option('--force', is_flag=True)
@click.option('--changeset')
def push(ctx, accounts, regions, names, force, changeset):
    """
    Create/Update live stacks
    """
    load_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    click.echo(f'Found {plural(count, "local stack")} to push')

    # We're only expecting 1 stack if a changeset is passed
    if changeset and len(found_stacks) != 1:
        click.echo(
            f'Error! The --changeset param was provided but {len(found_stacks)} stacks were found instead of 1'
        )
        exit(1)

    stack_descriptions = collections.defaultdict(dict)
    to_change = []

    for stack in found_stacks:
        ctx.obj.debug(
            f'Found {stack.name} in region {stack.region} with account number {stack.account_id}'
        )

        # If we have a small number of stacks, it's faster to just create changesets
        # to see if we have any updates that need to be performed
        if (len(found_stacks) > 20 or force or stack.purge):
            if stack.purge:
                ctx.obj.debug(f'Checking to see if {stack.name} still exists')
                if not stack.exists:
                    continue
            to_change.append(stack)
        # For a larger numer of stacks, describe stacks instead
        # and use the STAX_HASH tags to determine if updates need to be made
        else:
            key = '{stack.account},{stack.region}'
            if key not in stack_descriptions:
                cf = Cloudformation(account=stack.account, region=stack.region)
                with halo.Halo('Fetching stack status'):
                    stack_descriptions[key] = cf.describe_stacks()
            try:
                stax_hash = [
                    tag['Value']
                    for tag in stack_descriptions[key][stack.name]['Tags']
                    if tag['Key'] == 'STAX_HASH'
                ][0]
            except (KeyError, IndexError):
                stax_hash = None
            if stack.pending_update(stax_hash):
                to_change.append(stack)
    if not found_stacks:
        click.echo('No stacks found to update')
        sys.exit(1)

    click.echo('{} ... {}\n'.format(
        plural(len(to_change), 'stack needs an update',
               'stacks need an update'),
        [stack.name for stack in to_change] if to_change else ''))
    # Assume that update is more common than create and save some time
    for stack in to_change:
        if stack.purge is False:
            try:
                stack.diff
                stack.create_or_update(update=True,
                                       existing_changeset=changeset)
            except StackNotFound:
                stack.create_or_update(update=False)
            else:
                ctx.obj.debug(f'No change required for {stack.name}')
        else:
            if stack.exists:
                stack.delete()
