import collections
import datetime
import hashlib
import itertools
import json
import os
import pathlib
import string
import sys
import time
import uuid
import yaml

import boto3
import botocore
import click
import halo

from .connection_manager import get_client
from .. import gitlib
from ..exceptions import StackNotFound

yaml.add_multi_constructor('!', lambda loader, suffix, node: None)

SUCCESS_STATES = [
    'CREATE_COMPLETE',
    'DELETE_COMPLETE',
    'IMPORT_COMPLETE',
    'UPDATE_COMPLETE',
]

FAILURE_STATES = [
    'CREATE_FAILED',
    'DELETE_FAILED',
    'IMPORT_ROLLBACK_COMPLETE',
    'IMPORT_ROLLBACK_FAILED',
    'ROLLBACK_COMPLETE',
    'ROLLBACK_FAILED',
    'UPDATE_ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_FAILED',
]

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
        self.body = template_body
        self.file = template_file
        self.extn = 'json'

        if self.body and self.file:
            raise ValueError('You must specify one of either body or file')

    @property
    def raw(self):
        if not self.body:
            with open(self.file) as fh:
                self.body = fh.read()
        return self.body

    @property
    def to_dict(self):
        if isinstance(self.raw, str):
            try:
                return json.loads(self.raw)
            except:
                self.extn = 'yaml'
                return yaml.load(self.raw, Loader=yaml.BaseLoader)
        return self.raw


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
    def raw(self):
        return json.dumps(self.params)

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

    def to_list(self, extra_tags={}):
        if self.type != 'list' and self.tags is not None:
            return [{
                "Key": k,
                "Value": v
            } for k, v in {
                **extra_tags,
                **self.tags
            }.items()] if self.type is not None else None
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

    @property
    def bucket_client(self):
        """
        Return the bucket client
        """
        return get_client(self.bucket['profile'], self.bucket['region'], 's3')

    def gen_stack(self, stack_json):
        if stack_json['StackName'].startswith('StackSet'):
            raise ValueError(f'Ignoring StackSet {stack_json["StackName"]}')

        attempt = 0
        while True:
            try:
                raw_template = self.client.get_template(
                    StackName=stack_json['StackName'])['TemplateBody']
                break
            except botocore.exceptions.ClientError as err:
                if err.response['Error']['Message'].find('Throttling') != -1:
                    if attempt > 10:
                        raise
                    time.sleep(2 ^ attempt * 100)
                    attempt += 1
                else:
                    raise

        stack = Stack(
            name=stack_json['StackName'],
            account=self.account,
            region=self.region,
            params=stack_json.get('Parameters', None),
            template_body=raw_template,
        )

        # Ignore serverless
        try:
            stack.template.to_dict['Outputs']['ServerlessDeploymentBucketName']
        except:
            pass
        else:
            raise ValueError(
                f'Ignoring serverless stack {stack_json["StackName"]}')

        return stack

    def save_stack(self, stack, force):
        with open('stax.json', 'r') as fh_read:
            stack_json = json.load(fh_read)

        try:
            template_dest = string.Template(
                stack_json['stacks'][stack.name]['template']).substitute(
                    name=stack.name, account=stack.account)
            template_val = template_dest
        except:
            template_dest = f'{stack.account}/{stack.name}/template.{stack.template.extn}'
            template_val = f'$account/$name/template.{stack.template.extn}'
            pathlib.Path(f'{stack.account}/{stack.name}').mkdir(parents=True,
                                                                exist_ok=True)

        try:
            params_dest = string.Template(stack_json['stacks'][
                stack.name]['parameters'][stack.account]).substitute(
                    name=stack.name, account=stack.account)
            params_val = params_dest
        except:
            params_dest = f'{stack.account}/{stack.name}/params.json'
            params_val = f'$account/$name/params.json'
            pathlib.Path(f'{stack.account}/{stack.name}').mkdir(parents=True,
                                                                exist_ok=True)

        with open(template_dest, 'w') as fh:
            if stack.template.extn == 'yaml':
                # We can dump raw YAML - https://github.com/boto/boto3/issues/1468
                fh.write(stack.template.raw)
            else:
                # If the JSON template can be parsed, it's returned as a dict
                # so we can't return the original file, so we may as well pretty it
                json.dump(stack.template.to_dict, fh, indent=4)

        if stack.name not in stack_json['stacks']:
            stack_json['stacks'][stack.name] = {}
        if 'parameters' not in stack_json['stacks'][stack.name]:
            stack_json['stacks'][stack.name]['parameters'] = {}

        has_params = stack.params.to_dict
        if has_params:
            with open(params_dest, 'w') as fh:
                json.dump(has_params, fh, sort_keys=True, indent=4)
            stack_json['stacks'][stack.name]['parameters'][
                stack.account] = params_val
        else:
            stack_json['stacks'][stack.name]['parameters'][stack.account] = ''
        stack_json['stacks'][stack.name]['template'] = template_val
        if 'regions' not in stack_json['stacks'][stack.name]:
            stack_json['stacks'][stack.name]['regions'] = []
        if self.region not in stack_json['stacks'][stack.name]['regions']:
            stack_json['stacks'][stack.name]['regions'].append(self.region)

        with open('stax.json', 'w') as fh_write:
            json.dump(stack_json, fh_write, sort_keys=True, indent=4)

    def generate_stacks(self, local_stacks={}, stack_names=None, force=False):
        """
        Pull down a list of created AWS stacks, and
        generate the configuration locally
        """
        for _, remote_stack in self.describe_stacks(stack_names).items():
            if remote_stack['StackStatus'] in ['REVIEW_IN_PROGRESS']:
                print(
                    f'Skipping {remote_stack["StackName"]} due to {remote_stack["StackStatus"]} status'
                )
                continue
            try:
                parsed_stack = self.gen_stack(remote_stack)
            except ValueError as err:
                print(err)
                continue

            if force or parsed_stack not in local_stacks:
                click.echo(f'Saving stack {parsed_stack.name}')
                self.save_stack(parsed_stack, force)
            else:
                click.echo(
                    f'Skipping stack {parsed_stack.name} as it exists in stax.json - The live stack may differ, use --force to force'
                )

    def describe_stacks(self, names=None):
        """
        Describe existing stacks
        """
        results = {}
        list_of_stacks_to_describe = [{
            'StackName': name
        } for name in names] if names else [{}]
        for stack_to_describe in list_of_stacks_to_describe:
            paginator = self.client.get_paginator('describe_stacks')
            response_iterator = paginator.paginate(**stack_to_describe)
            try:
                results = {
                    **results,
                    **{
                        stack['StackName']: stack
                        for name in names for response in response_iterator for stack in response['Stacks']
                    }
                }
            except botocore.exceptions.ClientError as err:
                if err.response['Error']['Message'].find(
                        'does not exist') != -1:
                    raise StackNotFound(f'{name} stack does not exist')
                raise
        return results

    @property
    def exists(self):
        """
        Determine if an individual stack exists
        """
        try:
            if self.describe_stacks(name=self.name):
                return True
        except StackNotFound:
            return False

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

    @property
    def default_tags(self):
        """
        Return some default tags based on chosen CI
        """
        if 'buildkite' in self.context.config.get('ci', {}):
            return {
                "BUILDKITE_COMMIT":
                os.getenv("BUILDKITE_COMMIT", gitlib.current_branch()),
                "BUILDKITE_BUILD_URL":
                os.getenv("BUILDKITE_BUILD_URL", "dev"),
                "BUILDKITE_REPO":
                os.getenv("BUILDKITE_REPO", "dev"),
                "BUILDKITE_BUILD_CREATOR":
                os.getenv("BUILDKITE_BUILD_CREATOR", gitlib.user_email()),
                "STAX_HASH":
                self.hash_of_params_and_template,
            }
        return {}

    @property
    def resources(self):
        """
        Return stack resources
        """
        req = self.client.describe_stack_resources(StackName=self.name)
        return req['StackResources']

    def wait_for_stack_update(self, action=None):
        """
        Wait for a stack change/update
        """
        kwargs = {'text': '{self.name}: {action} Pending'}
        if action == 'deletion':
            kwargs['color'] = 'red'
        spinner = halo.Halo(**kwargs)
        spinner.start()

        while True:
            try:
                req = self.client.describe_stacks(StackName=self.name)
            except botocore.exceptions.ClientError as err:
                if err.response['Error']['Message'].find(
                        'does not exist') != -1:
                    if action == 'deletion':
                        return spinner.succeed(
                            f'{self.name}: DELETE_COMPLETE (or stack not found)'
                        )
                    raise StackNotFound(f'{self.name} stack no longer exists')
                raise

            status = req['Stacks'][0]['StackStatus']

            spinner.text = f'{self.name}: {status}'
            if status in FAILURE_STATES:
                return spinner.fail()
            elif status in SUCCESS_STATES:
                return spinner.succeed()

            time.sleep(1)

    def changeset_create_and_wait(self,
                                  set_type,
                                  use_existing_params=False,
                                  skip_tags=False):
        """
        Request a changeset, and wait for creation
        """
        spinner = halo.Halo(
            text=
            f'Creating {set_type.lower()} changeset for {self.name}/{self.account} in {self.region}'
        )
        spinner.start()
        # Create Changeset
        kwargs = dict(
            ChangeSetName=f'stax-{uuid.uuid4()}',
            StackName=self.name,
            Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
        )

        if len(self.template.raw) > 51200:
            kwargs['TemplateBody'] = self.template.raw
        else:
            kwargs[
                'TemplateURL'] = f'https://{self.bucket["name"]}.s3.{self.bucket["region"]}.amazonaws.com/stax/stax_template_{self.hash_of_template}'
            self.bucket_client.put_object(
                Body=self.template.raw,
                Bucket=self.bucket['name'],
                Key=f'stax/stax_template_{self.hash_of_template}')
        if use_existing_params:
            stack_describe = self.describe_stacks(name=self.name)[self.name]
            if 'Parameters' in stack_describe:
                kwargs['Parameters'] = stack_describe['Parameters'].copy()
                for param in kwargs['Parameters']:
                    param['UsePreviousValue'] = True
                    del (param['ParameterValue'])
                    if 'ResolvedValue' in param:
                        del (param['ResolvedValue'])
        else:
            params_passed = self.params.to_list
            if params_passed:
                kwargs['Parameters'] = params_passed

        if not skip_tags:
            tags_passed = self.tags.to_list(extra_tags=self.default_tags)
            if tags_passed:
                kwargs['Tags'] = tags_passed

        try:
            req = self.client.create_change_set(ChangeSetType=set_type,
                                                **kwargs)
            cs_id = req['Id']
        except botocore.exceptions.ClientError as err:
            err_msg = err.response['Error']['Message']
            spinner.fail(f'{self.name}: {err.response["Error"]["Message"]}')
            if err_msg.find('does not exist') != -1:
                #spinner.fail(f'{self.name} does not exist')
                raise StackNotFound(f'{self.name} stack no longer exists')
            sys.exit(1)

        # Wait for it to be ready
        while True:
            req = self.client.describe_change_set(ChangeSetName=cs_id)
            if req['Status'] not in ['CREATE_PENDING', 'CREATE_IN_PROGRESS']:
                break
            time.sleep(1)
        if 'StatusReason' in req and req['StatusReason'].find(
                "didn't contain changes") != -1:
            spinner.succeed(
                f'{self.name}/{self.account} in {self.region} is up to date!\n'
            )
            return
        spinner.succeed()

        investigate = parse_changeset_changes(req['Changes'])

        for thing in investigate:
            if thing == 'Tags':
                old_tags = self.describe_stacks(
                    name=self.name)[self.name]['Tags']
                new_tags = kwargs['Tags']
                differences = [
                    click.echo(f'{k}: \n' +
                               click.style(f'  - {old_tags[k]}\n', fg=red) +
                               click.style(f'  + {v}'))
                    for k, v in new_tags.items() if old_tags.get(k) != v
                ]

                f'Are you sure you want to {click.style("create", fg="green")} {self.account}/{self.name} in {self.region}?'

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
        self.wait_for_stack_update('deletion')

    def update(self, use_existing_params, skip_tags):
        """
        Update a stack via change set
        """
        # Create changeset
        changeset = self.changeset_create_and_wait(
            'UPDATE',
            use_existing_params=use_existing_params,
            skip_tags=skip_tags)

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
    def __init__(
        self,
        name,
        account,
        region,
        params=None,
        tags=None,
        template_body=None,
        template_file=None,
        bucket=None,
        purge=False,
    ):

        # Adopt parent class methods/attributes
        super().__init__()

        self.name = name
        self.account = account
        self.region = region

        self.params = Params(params=params)

        if [template_body, template_file].count(None) != 1:
            raise ValueError(
                'You must enter either template_body or template_file')

        if template_body:
            self.template = Template(template_body=template_body)
        else:
            s = string.Template(template_file)
            self.template = Template(
                template_file=s.substitute(name=name, account=account))

        self.bucket = bucket

        self.tags = Tags(tags=tags)

        self.purge = purge

    @property
    def hash_of_params_and_template(self):
        """
        Hash parameters and templates to quickly determine if a stack needs to be updated
        """
        return hashlib.sha256(
            self.template.raw.encode('utf-8') +
            self.params.raw.encode('utf-8')).hexdigest()

    @property
    def hash_of_template(self):
        """
        Hash template to use for bucket filename
        """
        return hashlib.sha256(self.template.raw.encode('utf-8')).hexdigest()

    def pending_update(self, stax_hash):
        """
        Determine if a stack needs to be updated by the lack or mismatch of `STAX_HASH` tag
        """
        if self.hash_of_params_and_template != stax_hash:
            return True
        return False

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
            cause = f'caused by changes to: {scope_and_causing_entities}'

            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be modified {mod_type}{cause}',
                fg='yellow')

            dig_into.extend(scope_and_causing_entities.keys())

        elif rc['Action'] == 'Remove':
            click.secho(
                f'{rc["ResourceType"]} ({rc["LogicalResourceId"]}) will be deleted',
                fg='red')
        else:
            raise ValueError('Unhandled change', change)
    return dig_into
