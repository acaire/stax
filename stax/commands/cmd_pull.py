"""
Pull AWS Cloudformation stacks to local state
"""
import click

from stax.commands.common import accounts_regions_and_names, class_filter
from stax.stack import Cloudformation, generate_stacks, load_stacks
from stax.utils import plural


@click.command()
@accounts_regions_and_names
@click.option('--force', is_flag=True)
def pull(ctx, accounts, regions, names, force):
    """
    Pull live stacks
    """

    load_stacks(ctx)
    count, found_stacks = class_filter(ctx.obj.stacks,
                                       account=accounts,
                                       region=regions,
                                       name=names)

    if count:
        click.echo(
            f'Found {plural(count, "existing local stack")} to be overwritten')

    for account in accounts:
        click.echo(f'pulling account {account}')
        for region in regions:
            click.echo(f'pulling region {region}')
            cf = Cloudformation(account=account, region=region)
            remote_stacks = cf.describe_stacks(names=names)
            generate_stacks(cf,
                            local_stacks=found_stacks,
                            remote_stacks=remote_stacks,
                            stack_names=names,
                            force=force)
