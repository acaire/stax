"""
AWS Cloudformation Changeset utils
"""

import click


def parse_changeset_changes(changes):
    """
    Parse a changeset for changes
    and highlight what has been added,
    modified and removed
    """
    # Find out more about these attributes
    dig_into = []

    for change in changes:
        rc = change['ResourceChange']
        if rc['Action'] == 'Add':
            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be added',
                fg='green')
        elif rc['Action'] == 'Modify':
            mod_type = click.style(
                'by deletion and recreation ',
                fg='red') if rc['Replacement'] in ['True', True] else ''

            scope_and_causing_entities = {
                scope: [
                    detail['CausingEntity'] for detail in rc['Details']
                    if 'CausingEntity' in rc
                ]
                for scope in rc['Scope']
            }
            cause_string = ', '.join([
                k if not v else k + v
                for k, v in scope_and_causing_entities.items()
            ])
            cause = f'caused by changes to: {cause_string}'

            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be modified {mod_type}{cause}',
                fg='yellow')

            dig_into.extend([key for key in scope_and_causing_entities.keys()])

        elif rc['Action'] == 'Remove':
            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be deleted',
                fg='red')
        else:
            click.echo(
                'Please raise an issue for the following unhandled change:\n',
                change)
    return dig_into
