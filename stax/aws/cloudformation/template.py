"""
AWS Cloudformation Template
"""

import json

import yaml


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
    def string(self):
        if self.extn == 'json':
            if isinstance(self.raw, str):
                return self.raw
            return json.dumps(self.raw, sort_keys=True, indent=4)
        return yaml.dumps(self.raw)

    @property
    def to_dict(self):
        if isinstance(self.raw, str):
            try:
                return json.loads(self.raw)
            except:
                self.extn = 'yaml'
                return yaml.load(self.raw, Loader=yaml.BaseLoader)
        return self.raw
