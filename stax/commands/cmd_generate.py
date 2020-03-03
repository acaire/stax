'''
Generate a sample stax.json file
'''
import click
import json


@click.command()
def generate():
    '''
    Generate a sample stax.json file
    '''
    content = dict(
        accounts={
            'development': {
                'id': '123',
                'profile': 'dev_profile'
            },
            'staging': {
                'id': '456',
                'profile': 'staging_profile'
            },
            'production': {
                'id': '789',
                'profile': 'prod_profile'
            },
        },
        default_region='ap-southeast-2',
        stacks={
            'my_first_stack_with_no_params': {
                'parameters': {
                    'development': '',
                },
                'template': 'my_first_stack.json',
            },
            'my_second_stack_with_params': {
                'parameters': {
                    'staging': {
                        'REDIS_USERNAME': 'example'
                    },
                    'production': 'my_second_stack-prod.json'
                },
                'template': 'my_second_stack.json',
            }
        },
    )
    click.echo(json.dumps(content, sort_keys=True, indent=4))
