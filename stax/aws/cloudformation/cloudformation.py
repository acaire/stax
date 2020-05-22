import collections
import datetime
import difflib
import hashlib
import itertools
import json
import os
import pathlib
import string
import sys
import textwrap
import time
import uuid

import arrow
import boto3
import botocore
import click
import halo
import yaml

from stax import gitlib
from stax.aws.cloudformation.params import Params
from stax.aws.cloudformation.tags import Tags
from stax.aws.cloudformation.template import Template
from stax.exceptions import StackNotFound
from stax.utils import get_diff, plural, print_diff

from ..connection_manager import get_client
from .changeset import parse_changeset_changes

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

# Handle Cloudformation YAML tags - https://git.io/JfBIC
yaml.add_multi_constructor('!', lambda loader, suffix, node: None)


class Cloudformation:
    """
    Class for actions to do with Cloudformation
    """
    def __init__(self, account=None, region=None):
        self.account = account
        self.region = region
        self._remote_account_id = None

    @property
    def remote_account_id(self):
        if self._remote_account_id is None:
            sts_client = get_client(self.profile, self.region, 'sts')
            self._remote_account_id = sts_client.get_caller_identity().get(
                'Account')
        return self._remote_account_id

    @property
    def client(self):
        """
        Return a client
        """
        if 'id' in self.context.config['accounts'][self.account]:
            if self.context.config['accounts'][
                    self.account]['id'] != self.remote_account_id:
                click.echo(click.style(textwrap.dedent(f"""
                    Profile mismatch for {self.account} account:
                         Expected AWS ID: {self.context.config["accounts"][self.account]["id"]}
                            Found AWS ID: {self.remote_account_id}
                    """),
                                       fg='red'),
                           err=True)
                exit(1)
        return get_client(self.profile, self.region, 'cloudformation')

    @property
    def bucket_client(self):
        """
        Return the bucket client
        """
        return get_client(self.bucket['profile'], self.bucket['region'], 's3')

    def describe_stacks(self, names=None):
        """
        Describe existing stacks
        """
        results = {}
        list_of_kwargs = [{
            'StackName': name
        } for name in names] if names is not None else [{}]
        for kwargs in list_of_kwargs:
            paginator = self.client.get_paginator('describe_stacks')
            response_iterator = paginator.paginate(**kwargs)
            try:
                for response in response_iterator:
                    for stack in response['Stacks']:
                        results[stack['StackName']] = stack
            except botocore.exceptions.ClientError as err:
                if err.response['Error']['Message'].find(
                        'does not exist') != -1:
                    raise StackNotFound(
                        f'{kwargs["StackName"]} stack does not exist')
                raise
        return results

    @property
    def description(self):
        if not self._description:
            self._description = self.describe_stacks(
                names=[self.name])[self.name]
        return self._description

    @property
    def describe(self):
        """
        Describe this stack
        """
        return self.describe_stacks(names=[self.name])[self.name]

    @property
    def exists(self):
        """
        Determine if an individual stack exists
        """
        try:
            if self.description:
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
    def live_params(self):
        """
        Return live params
        """
        # convert OrderedDict to dict
        #params = Params(values=[dict(param) for param in self.description.get('Parameters', [])])
        params = Params(values=self.description.get('Parameters', []))
        return params

    @property
    def live_template(self):
        """
        Return live params
        """
        template = Template(template_body=self.client.get_template(
            StackName=self.name)['TemplateBody'])
        return template

    @property
    def diff(self):
        if self.exists:
            diffs = []
            diffs.append(
                get_diff(self.live_params.to_dict, self.params.to_dict,
                         'params'))
            diffs.append(
                get_diff(self.live_tags.to_dict, self.tags.to_dict, 'tags'))
            diffs.append(
                get_diff(self.live_template.to_dict, self.template.to_dict,
                         'template'))
            for diff in diffs:
                print_diff(diff)

    @property
    def live_tags(self):
        """
        Return live tags
        """
        return Tags(values=self.description.get('Tags', []))

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
                os.getenv("BUILDKITE_REPO", f"{gitlib.remotes()}"),
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
        if not self._resources:
            req = self.client.describe_stack_resources(StackName=self.name)
            self._resources = req['StackResources']
        return self._resources

    def wait_for_stack_update(self, action=None):
        """
        Wait for a stack change/update
        """
        kwargs = {'text': '{self.name}: {action} Pending'}
        if action == 'deletion':
            kwargs['color'] = 'red'

        with halo.Halo(**kwargs) as spinner:
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
                        raise StackNotFound(
                            f'{self.name} stack no longer exists')
                    raise

                status = req['Stacks'][0]['StackStatus']

                spinner.text = f'{self.name}: {status}'
                if status in FAILURE_STATES:
                    return spinner.fail()
                elif status in SUCCESS_STATES:
                    return spinner.succeed()
                time.sleep(1)

    def wait_for_changeset_to_be_ready(self, cs_id):
        while True:
            req = self.client.describe_change_set(ChangeSetName=cs_id)
            if req['Status'] not in ['CREATE_PENDING', 'CREATE_IN_PROGRESS']:
                break
            time.sleep(1)
        if 'StatusReason' in req and req['StatusReason'].find(
                "didn't contain changes") != -1:
            return
        return req

    def look_into_changeset_stuff(self, req):
        investigate = parse_changeset_changes(req['Changes'])
        #print(investigate)

        old_template = self.client.get_template(
            StackName=self.name)['TemplateBody']
        new_template = self.template.raw

        if self.template.extn == 'yaml':
            old_template = yaml.dump(old_template, indent=4, sort_keys=True)
        elif isinstance(old_template, str):
            old_template = json.dumps(json.loads(old_template),
                                      indent=4,
                                      sort_keys=True)
        else:
            old_template = json.dumps(old_template, indent=4, sort_keys=True)

        if self.template.extn == 'yaml':
            new_template = yaml.dump(new_template, indent=4, sort_keys=True)
        elif isinstance(new_template, str):
            new_template = json.dumps(json.loads(new_template),
                                      indent=4,
                                      sort_keys=True)
        else:
            new_template = json.dumps(new_template, indent=4, sort_keys=True)

        my_diff = get_diff(old_template,
                           new_template,
                           'template_',
                           fmt=self.template.extn)

        my_diff = get_diff(
            Params(values=self.description.get('Parameters', [])).to_dict,
            self.params.to_dict,
            fmt=self.template.extn)

        return req['ChangeSetId']

    def changeset_create_and_wait(self,
                                  set_type,
                                  existing_params=False,
                                  existing_template=True):
        """
        Request a changeset, and wait for creation
        """
        with halo.Halo(
                f'Creating {set_type.lower()} changeset for {self.name}/{self.account} in {self.region}'
        ) as spinner:
            kwargs = dict(
                ChangeSetName=f'stax-{uuid.uuid4()}',
                StackName=self.name,
                Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            )

            if existing_template:
                kwargs['UsePreviousTemplate'] = True
            else:
                # Large templates need to be pushed to S3 first - https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cloudformation-limits.html
                template_size_limit = 51200
                if len(self.template.raw) <= template_size_limit:
                    kwargs['TemplateBody'] = self.template.raw
                else:
                    if not self.bucket['name']:
                        click.echo(
                            'The template for this file is {len(self.template.raw)}, which is larger than {template_size_limit}'
                        )
                        exit(1)
                    kwargs[
                        'TemplateURL'] = f'https://{self.bucket["name"]}.s3.{self.bucket["region"]}.amazonaws.com/stax/stax_template_{self.hash_of_template}'
                    self.bucket_client.put_object(
                        Body=self.template.raw,
                        Bucket=self.bucket['name'],
                        Key=f'stax/stax_template_{self.hash_of_template}')

            if existing_params:
                kwargs[
                    'Parameters'] = self.live_params.to_list_with_previous_values
            else:
                kwargs['Parameters'] = self.params.to_list

            if not existing_template and not existing_params:
                kwargs['Tags'] = self.tags.to_list

            try:
                req = self.client.create_change_set(ChangeSetType=set_type,
                                                    **kwargs)
                cs_id = req['Id']
            except botocore.exceptions.ClientError as err:
                err_msg = err.response['Error']['Message']
                spinner.fail(
                    f'{self.name}: {err.response["Error"]["Message"]}')
                if err_msg.find('does not exist') != -1:
                    spinner.fail(f'{self.name} no longer exists')
                    raise StackNotFound(f'{self.name} stack no longer exists')
                sys.exit(1)

            changeset_req = self.wait_for_changeset_to_be_ready(cs_id)
            if changeset_req is None:
                spinner.succeed(
                    f'{self.name}/{self.account} in {self.region} is up to date!\n'
                )
            else:
                spinner.succeed(
                    f'{self.name}/{self.account} changeset created!\n')
            return changeset_req

    def create(self, changeset):
        """
        Create a stack via change set
        """
        if changeset:
            cs_describe = self.client.describe_change_set(
                ChangeSetName=changeset)
            if cs_describe['StackName'] != self.name:
                click.echo(
                    f'Changeset stack name {cs_describe["StackName"]} does not match {self.name}'
                )
                exit(1)
            elif self.context.config['ci']['changeset_timeout'] and arrow.get(
                    cs_describe['CreationTime']).shift(
                        minutes=self.context.config['ci']
                        ['changeset_timeout']) > arrow.now():
                click.echo(
                    f'Refusing to execute changeset that is older than {plural(self.context.config["ci"]["changeset_timeout"], "minute")} ({arrow.get(cs_describe["CreationTime"]).to("local")})'
                )
                exit(1)
        else:
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
        Delete a stack
        """
        if not click.confirm(
                f'Are you sure you want to {click.style("delete", fg="red")} {self.account}/{self.name} in {self.region}?'
        ):
            return
        with halo.Halo(f'Deleting {self.name} in {self.region}') as spinner:
            req = self.client.delete_stack(StackName=self.name)
            self.wait_for_stack_update('deletion')
            spinner.succeed(f'{self.name} deleted')

    def create_or_update(self,
                         update,
                         existing_changeset=None,
                         existing_params=False,
                         existing_template=False):
        """
        Create or Update a stack via change set
        """
        if update:
            set_type = 'update'
        else:
            set_type = 'create'
        if existing_changeset:
            changeset = existing_changeset
            req = self.wait_for_changeset_to_be_ready(changeset)
            cs_describe = self.client.describe_change_set(
                ChangeSetName=changeset)
            if cs_describe['StackName'] != self.name:
                click.echo(
                    f'Changeset stack name {cs_describe["StackName"]} does not match {self.name}'
                )
                exit(1)
            elif self.context.config['ci']['changeset_timeout'] and arrow.get(
                    cs_describe['CreationTime']).shift(
                        minutes=self.context.config['ci']
                        ['changeset_timeout']) < arrow.now():
                click.echo(
                    f'Refusing to execute changeset that is older than {plural(self.context.config["ci"]["changeset_timeout"], "minute")} ({arrow.get(cs_describe["CreationTime"]).to("local")})'
                )
                exit(1)
        else:
            changeset = self.changeset_create_and_wait(
                set_type.upper(),
                existing_params=existing_params,
                existing_template=existing_template)

        if changeset and set_type == 'update':
            self.look_into_changeset_stuff(changeset)

        if not changeset:
            return

        if not click.confirm(
                f'Are you sure you want to {click.style("update", fg="cyan" if update else "green")} {click.style(self.account, bold=True)}/{self.name} in {self.region}?'
        ):
            if not existing_changeset:
                with halo.Halo('Deleting changeset') as spinner:
                    self.client.delete_change_set(
                        ChangeSetName=changeset['ChangeSetId'],
                        StackName=self.name)
                    spinner.succeed('Changeset deleted')
            return

        # Execute changeset
        req = self.client.execute_change_set(
            ChangeSetName=changeset['ChangeSetId'])

        # Wait for changes
        self.wait_for_stack_update()
