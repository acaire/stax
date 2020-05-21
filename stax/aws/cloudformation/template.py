"""
AWS Cloudformation Template
"""

import json

import yaml


class Template:
    def __init__(self, template_body=None, template_file=None):
        self.body = template_body
        self.filename = template_file
        self.extn = 'json'

        if self.body and self.filename:
            raise ValueError(
                'You must specify one of either template_body or template_file'
            )

    @property
    def raw(self):
        if not self.body:
            with open(self.filename) as fh:
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
