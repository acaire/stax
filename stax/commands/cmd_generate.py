'''
Generate a sample stax.json file
'''
import json
import os

import click


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
            'the_name_of_stack_1_that_uses_the_default_region': {
                'parameters': {
                    'development': '',
                },
                'template': 'my_stack_which_does_not_require_params.json',
            },
            'the_name_of_stack_2_that_uses_the_default_region': {
                'parameters': {
                    'staging': {
                        'REDIS_USERNAME': 'this_is_an_example_param_value'
                    },
                    'production': 'this_is_how_to_use_a_file_instead.json'
                },
                'template': 'my_second_stack.json',
            },
            'the_name_of_stack_3_that_uses_a_specific_region': {
                'parameters': {
                    'development': "",
                },
                'region': 'us-east-1',
                'template': 'my_third_stack_with_a_specific_region.json',
            }
        },
    )
    click.echo(json.dumps(content, sort_keys=True, indent=4))
    if os.fstat(0) == os.fstat(1):
        click.echo(
            click.style('Redirect to stax.json to save this file', bold=True))
