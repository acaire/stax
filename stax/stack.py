import hashlib
import json
import pathlib
import string

import click

from stax.aws.cloudformation.cloudformation import Cloudformation
from stax.aws.cloudformation.params import Params
from stax.aws.cloudformation.tags import Tags
from stax.aws.cloudformation.template import Template


def save_stack(stack, force):
    with click.open_file('stax.json', 'r') as fh_read:
        stack_json = json.load(fh_read)

    region_and_account = f'{stack.region}/{stack.account}'

    template_dest = pathlib.Path(
        f'{stack.account}/{stack.name}/template.{stack.template.extn}')

    params_dest = pathlib.Path(f'{stack.account}/{stack.name}/params.json')

    has_params = stack.params.to_dict
    if has_params:
        no_echo_cmds = [k for k, v in has_params.items() if v == '*' * 4]
        if no_echo_cmds and not click.confirm(
            ('The following params have been saved with NoEcho'
             f'  {no_echo_cmds} Do you wish to retrieve them?')):
            print('Exiting without saving NoEcho params')
            exit(1)
        else:
            stack.create_or_update(update=True,
                                   existing_params=True,
                                   existing_template=True)

        params_dest.parent.mkdir(parents=True, exist_ok=True)
        with click.open_file(params_dest, 'w') as fh:
            json.dump(has_params, fh, sort_keys=True, indent=4)
    else:
        params_dest = ''

    generate_json = {
        'parameters': {
            region_and_account: str(params_dest)
        },
        'template': str(template_dest)
    }

    if stack.name not in stack_json['stacks']:
        stack_json['stacks'][stack.name] = generate_json

    with click.open_file(template_dest, 'w') as fh:
        template_dest.parent.mkdir(parents=True, exist_ok=True)
        if stack.template.extn == 'yaml':
            yaml.dump(stack.template)
        else:
            json.dump(stack.template.to_dict, fh, indent=4)

    with click.open_file('stax.json', 'w') as fh_write:
        json.dump(stack_json, fh_write, sort_keys=True, indent=4)


def load_stacks(ctx):
    ctx.obj.stacks = []

    for name, stack in ctx.obj.config['stacks'].items():
        for region_and_account, params_value in stack['parameters'].items():
            try:
                region, account = region_and_account.split('/')
            except ValueError:
                account = region_and_account
                region = ctx.obj.config['default_region']

            kwargs = {}

            # Check for tags dict or string (file)
            tags = stack.get('tags', {})
            if isinstance(tags, str):
                kwargs['tags_file'] = tags
            else:
                kwargs['tags_dict'] = tags

            # Check for params dict or string (file)
            if isinstance(params_value, str):
                kwargs['params_file'] = params_value
            else:
                kwargs['params_dict'] = params_value

            ctx.obj.stacks.append(
                Stack(name=name,
                      account=account,
                      bucket=stack.get('bucket',
                                       ctx.obj.config.get('default_bucket')),
                      purge=stack.get('purge', False),
                      region=region,
                      template_file=stack['template'],
                      **kwargs))


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
        params_dict=None,
        params_file=None,
        tags_dict=None,
        tags_file=None,
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

        self._description = None

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

        if params_dict:
            self.params = Params(values=params_dict)
        else:
            self.params = Params(filename=params_file)

        if tags_dict:
            self._tags = Tags(values=tags_dict)
        else:
            self._tags = Tags(filename=tags_file)

        self.purge = purge

    @property
    def tags(self):
        return Tags(values={**self._tags.to_dict, **self.default_tags})

    @property
    def hash_of_params_and_template(self):
        """
        Hash parameters and templates to quickly determine if a stack needs to be updated
        """
        return hashlib.sha256(
            json.dumps(self.template.to_dict).encode('utf-8') +
            json.dumps(self.params.to_dict).encode('utf-8')).hexdigest()

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


def generate_stacks(cf,
                    remote_stacks,
                    local_stacks={},
                    stack_names=None,
                    force=False):
    """
    Pull down a list of created AWS stacks, and
    generate the configuration locally
    """
    for _, remote_stack in remote_stacks.items():
        if remote_stack['StackStatus'] in ['REVIEW_IN_PROGRESS']:
            click.echo(
                f'Skipping {remote_stack["StackName"]} due to {remote_stack["StackStatus"]} status'
            )
            continue
        try:
            parsed_stack = gen_stack(cf, remote_stack)
        except ValueError as err:
            click.echo(err)
            continue

        if force or parsed_stack not in local_stacks:
            click.echo(f'Saving stack {parsed_stack.name}')
            save_stack(parsed_stack, force)
        else:
            click.echo(
                f'Skipping stack {parsed_stack.name} as it exists in stax.json - The live stack may differ, use --force to force'
            )


def gen_stack(cf, stack_json):
    if stack_json['StackName'].startswith('StackSet'):
        raise ValueError(f'Ignoring StackSet {stack_json["StackName"]}')

    attempt = 0
    while True:
        try:
            raw_template = cf.client.get_template(
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

    return Stack(
        name=stack_json['StackName'],
        account=cf.account,
        region=cf.region,
        params_dict=stack_json.get('Parameters', None),
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
