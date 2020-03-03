import collections
import json
import sys
import time
import uuid
import yaml

import boto3
import botocore
import click
import datetime

from .connection_manager import get_client
from ..exceptions import StackNotFound

DEFAULT_AWS_REGIONS = [
    'ap-northeast-1',
    'ap-northeast-2',
    'ap-south-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'ca-central-1',
    'eu-central-1',
    'eu-north-1',
    'eu-west-1',
    'eu-west-2',
    'eu-west-3',
    'sa-east-1',
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2',
]


class Template:
    def __init__(self, template_body=None, template_file=None):
        """
        Assemble a Template class by either passing in a:
          string - To convert to a template dict
          dict   - To parse as JSON
        """
        self.body = template_body
        self.file = template_file

        if self.body and self.file:
            raise ValueError('You must specify one of either body or file')

    @property
    def raw(self):
        if self.body:
            return self.body
        else:
            with open(self.file) as fh:
                return fh.read()

    @property
    def to_dict(self):
        return json.loads(self.raw)

    @property
    def to_troposphere(self):
        """
        Return Troposphere parsed object
        """
        try:
            return TemplateGenerator(self.to_dict)
        except:
            raise ValueError(f'{self.name} failed on template {self.template}')


class Params:
    def __init__(self, params):
        """
        Assemble a Params class by either passing in a:
          string - To read a filename of dict values
          dict   - To read a dict of {k: v} values
          list   - To read a list of {ParameterName: foo, ParameterValue: bar} dicts
        """
        self.params = params

        if self.params is None or self.params == '':
            self.type = 'dict'
            self.params = None
        elif isinstance(self.params, str):
            self.type = 'file'
        elif isinstance(self.params, list):
            self.type = 'list'
        elif isinstance(self.params, dict):
            self.type = 'dict'
        elif self.params is None:
            self.type = 'dict'
        else:
            raise ValueError('Unexpected value for Params class')

    @property
    def to_dict(self):
        if self.type == 'file':
            with open(self.params) as fh:
                return json.load(fh)
        elif self.type == 'list':
            return {
                param['ParameterKey']: param['ParameterValue']
                for param in self.params
            }
        return self.params

    @property
    def to_list(self):
        if self.type in ['file', 'dict'] and self.params is not None:
            return [{
                "ParameterKey": k,
                "ParameterValue": v
            } for k, v in self.to_dict.items()
                    ] if self.type is not None else None
        return self.params


class Tags:
    def __init__(self, tags):
        """
        Assemble a Params class by either passing in a:
          dict   - To read a dict of {k: v} values
          list   - To read a list of {TagName: foo, TagValue: bar} dicts
        """
        self.tags = tags

        if isinstance(self.tags, dict) or self.tags is None:
            self.type = 'dict'
        elif isinstance(self.tags, list):
            self.type = 'list'
        else:
            raise ValueError(
                f'Unexpected {type(self.tags)} value for Tags class')

    @property
    def to_dict(self):
        if self.type == 'list':
            return {tag['Key']: tag['Value'] for tag in self.tags}
        return self.tags

    @property
    def to_list(self):
        if self.type != 'list' and self.tags is not None:
            return [{
                "Key": k,
                "Value": v
            } for k, v in self.tags.items()] if self.type is not None else None
        return self.tags


class Cloudformation:
    """
    Class for actions to do with Cloudformation
    """
    def __init__(self, account=None, region=None):
        self.account = account
        self.region = region

    @property
    def client(self):
        """
        Return a client
        """
        return get_client(self.profile, self.region, 'cloudformation')

    def gen_stack(self, stack_json):
        template_json = self.client.get_template(
            StackName=stack_json['StackName'])['TemplateBody']
        if stack_json['StackName'].startswith('StackSet'):
            raise ValueError(f'Ignoring StackSet {stack_json["StackName"]}')
        try:
            template_json['Outputs']['ServerlessDeploymentBucketName']
        except:
            pass
        else:
            raise ValueError(
                f'Ignoring serverless stack {stack_json["StackName"]}')
        template_body = json.dumps(template_json)
        return Stack(
            name=stack_json['StackName'],
            account=self.account,
            region=self.region,
            params=stack_json.get('Parameters', None),
            template_body=template_body,
        )

    def save_stack(self, stack):
        try:
            template_dest = f'aws/{stack.name}.{stack.account}.json'
            with open(template_dest, 'w') as fh:
                json.dump(stack.template.to_dict, fh, sort_keys=True, indent=4)
        except (json.decoder.JSONDecodeError, TypeError,
                yaml.constructor.ConstructorError):
            raise
            # Just write it out, perhaps it's YAML
            template_dest = f'aws/{stack.name}.{stack.account}.yaml'
            with open(template_dest, 'w') as fh:
                fh.write(stack.template_body)
        has_params = stack.params.to_dict
        if has_params:
            with open(f'new-params/{stack.name}.{stack.account}.json',
                      'w') as fh:
                json.dump(has_params, fh, sort_keys=True, indent=4)

        with open('stax.json', 'r') as fh_read:
            stack_json = json.load(fh_read)
            if stack.name not in stack_json['stacks']:
                stack_json['stacks'][stack.name] = {}
            if 'parameters' not in stack_json['stacks'][stack.name]:
                stack_json['stacks'][stack.name]['parameters'] = {}
            if has_params:
                stack_json['stacks'][stack.name]['parameters'][
                    stack.
                    account] = f'new-params/{stack.name}.{stack.account}.json'
            else:
                stack_json['stacks'][stack.name]['parameters'][
                    stack.account] = ''
            stack_json['stacks'][stack.name]['template'] = template_dest
            if 'regions' not in stack_json['stacks'][stack.name]:
                stack_json['stacks'][stack.name]['regions'] = []
            if self.region not in stack_json['stacks'][stack.name]['regions']:
                stack_json['stacks'][stack.name]['regions'].append(self.region)
            with open('stax.json', 'w') as fh_write:
                json.dump(stack_json, fh_write, sort_keys=True, indent=4)

    def generate_stacks(self, local_stacks={}, stack_name=None, force=False):

        for remote_stack in self.describe_stacks(stack_name):
            try:
                parsed_stack = self.gen_stack(remote_stack)
            except ValueError as err:
                print(err)
                continue

            if force or parsed_stack not in local_stacks:
                click.echo(f'Saving stack {parsed_stack.name}')
                self.save_stack(parsed_stack)
            else:
                click.echo(
                    f'Skipping stack {parsed_stack.name} as it exists in stax.json - The live stack may differ, use --force to force'
                )

    def describe_stacks(self, name):
        """
        Describe existing stacks
        """
        kwargs = {}
        if name:
            kwargs['StackName'] = name

        paginator = self.client.get_paginator('describe_stacks')
        response_iterator = paginator.paginate(**kwargs)

        try:
            return sorted([
                stack for response in response_iterator
                for stack in response['Stacks']
            ],
                          key=lambda k: k['StackName'])
        except botocore.exceptions.ClientError as err:
            if err.response['Error']['Message'].find('does not exist') != -1:
                click.echo(f'{name} stack does not exist')
                return []
            raise

    @property
    def context(self):
        """
        Return the click context
        """
        return click.get_current_context().obj

    @property
    def account_id(self):
        """
        Return the configured account ID
        """
        return self.context.config['accounts'][self.account]['id']

    @property
    def profile(self):
        """
        Return the configured account profile
        """
        return self.context.config['accounts'][self.account]['profile']

    def wait_for_stack_update(self):
        """
        Wait for a stack change/update
        """
        while True:
            try:
                req = self.client.describe_stacks(StackName=self.name)
            except botocore.exceptions.ClientError as err:
                if err.response['Error']['Message'].find(
                        'does not exist') != -1:
                    raise StackNotFound(f'{self.name} stack no longer exists')
                raise

            status = req['Stacks'][0]['StackStatus']
            if status.endswith(('FAILED', 'COMPLETE')):
                break
            time.sleep(1)
        if status in ['CREATE_COMPLETE']:
            click.secho('Stack created ✅', fg='green')
        elif status.endswith(('FAILED')):
            click.secho('Stack failed ❌', fg='red')

    def changeset_create_and_wait(self, set_type):
        """
        Request a changeset, and wait for creation
        """
        print(
            f'Creating {set_type.lower()} changeset for {self.name} in {self.region}'
        )
        # Create Changeset
        kwargs = dict(
            ChangeSetName=f'stax-{uuid.uuid4()}',
            StackName=self.name,
            TemplateBody=self.template.raw,
            Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
        )
        params_passed = self.params.to_list
        if params_passed:
            kwargs['Parameters'] = params_passed

        tags_passed = self.tags.to_list
        if tags_passed:
            kwargs['Tags'] = tags_passed

        try:
            req = self.client.create_change_set(ChangeSetType=set_type,
                                                **kwargs)
            cs_id = req['Id']
        except botocore.exceptions.ClientError as err:
            err_msg = err.response['Error']['Message']
            if err_msg.find('does not exist') != -1:
                raise StackNotFound(f'{self.name} stack no longer exists')
            raise

        # Wait for it to be ready
        while True:
            req = self.client.describe_change_set(ChangeSetName=cs_id)
            if req['Status'] not in ['CREATE_PENDING', 'CREATE_IN_PROGRESS']:
                break
            time.sleep(1)
        if 'StatusReason' in req and req['StatusReason'].find(
                "didn't contain changes") != -1:
            click.echo(f'{self.name} in {self.region} is up to date')
            return

        parse_changeset_changes(req['Changes'])
        return cs_id

    def create(self):
        """
        Create a stack via change set
        """
        # Create changeset
        changeset = self.changeset_create_and_wait('CREATE')

        if not changeset:
            return

        if not click.confirm(
                f'Are you sure you want to {click.style("create", fg="green")} {self.account}/{self.name} in {self.region}?'
        ):
            self.client.delete_change_set(ChangeSetName=changeset,
                                          StackName=self.name)
            self.context.debug(f'Deleted changeset {changeset}')
            return

        # Execute changeset
        req = self.client.execute_change_set(ChangeSetName=changeset)

        # Wait for changes
        self.wait_for_stack_update()

    def delete(self):
        """
        Create a stack via change set
        """
        if not click.confirm(
                f'Are you sure you want to {click.style("delete", fg="red")} {self.account}/{self.name} in {self.region}?'
        ):
            return
        click.echo(f'Deleting {self.name} in {self.region}')
        req = self.client.delete_stack(StackName=self.name)
        self.wait_for_stack_update()

    def update(self):
        """
        Update a stack via change set
        """
        # Create changeset
        changeset = self.changeset_create_and_wait('UPDATE')

        if not changeset:
            return

        if not click.confirm(
                f'Are you sure you want to {click.style("update", fg="cyan")} {click.style(self.account, bold=True)}/{self.name} in {self.region}?'
        ):
            self.client.delete_change_set(ChangeSetName=changeset,
                                          StackName=self.name)
            self.context.debug(f'Deleted changeset {changeset}')
            return

        # Execute changeset
        req = self.client.execute_change_set(ChangeSetName=changeset)

        # Wait for changes
        self.wait_for_stack_update()


class Stack(Cloudformation):
    """
    Stack class to represent how we define stacks as humans
    not how AWS expects them to be
    """
    def __init__(self,
                 name,
                 account,
                 region,
                 params=None,
                 tags=None,
                 template_body=None,
                 template_file=None):

        # Adopt parent class methods/attributes
        super().__init__()

        self.name = name
        self.account = account
        self.region = region

        self.params = Params(params=params)
        self.tags = Tags(tags=tags)

        if [template_body, template_file].count(None) != 1:
            raise ValueError(
                'You must enter either template_body or template_file')

        if template_body:
            self.template = Template(template_body=template_body)
        else:
            self.template = Template(template_file=template_file)

    def __members(self):
        return (self.account, self.region, self.name)

    def __eq__(self, other):
        """
        Determine equivalence by AWS' unique stack perspective
        """
        if type(self) is type(other):
            return self.__members() == other.__members()

    def __hash__(self):
        return hash(self.__members())

    def __repr__(self):
        """
        Friendly repr
        """
        return f'{self.account}/{self.region}/{self.name}'


def parse_changeset_changes(changes):
    """
    Parse a changeset for changes
    and highlight what has been added,
    modified and removed
    """
    for change in changes:
        rc = change['ResourceChange']
        if rc['Action'] == 'Add':
            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be added',
                fg='green')
        elif rc['Action'] == 'Modify':
            deletion = click.style(
                'by deletion and recreation',
                fg='red') if rc['Replacement'] in ['True', True] else ''
            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be modified {deletion}',
                fg='yellow')
        elif rc['Action'] == 'Remove':
            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be deleted',
                fg='red')
        else:
            raise ValueError('Unhandled change')
