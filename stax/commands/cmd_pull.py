"""
Pull AWS Cloudformation stacks to local state
"""
import click

from ..aws.cloudformation import Cloudformation
from ..utils import class_filter, accounts_regions_and_names, set_stacks, plural


@click.command()
@accounts_regions_and_names
@click.option('--force', is_flag=True)
def pull(ctx, accounts, regions, names, force):
    """
    Pull live stacks
    """

    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    click.echo(f'Found {plural(count, "existing local stack")}')

    for account in accounts:
        print('pulling account', account)
        for region in regions:
            print('pulling region', region)
            cf = Cloudformation(account=account, region=region)
            cf.generate_stacks(local_stacks=found_stacks,
                               stack_names=names,
                               force=force)
