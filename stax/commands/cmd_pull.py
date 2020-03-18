"""
Pull AWS Cloudformation stacks to local state
"""
import click

from ..aws.cloudformation import Cloudformation
from ..utils import class_filter, stack_options, set_stacks, plural


@click.command()
@stack_options
@click.argument('name', required=False)
@click.option('--force', is_flag=True)
def pull(ctx, accounts, regions, name, force):
    """
    Pull live stacks
    """

    set_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=name)

    click.echo(f'Found {plural(count, "existing local stack")}')

    for account in accounts:
        print('pulling account', account)
        for region in regions:
            print('pulling region', region)
            cf = Cloudformation(account=account, region=region)
            cf.generate_stacks(local_stacks=found_stacks,
                               stack_name=name,
                               force=force)
