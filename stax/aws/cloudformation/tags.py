"""
AWS Cloudformation Tags
"""

import json

import click

from stax.utils import dict_to_list, list_to_dict


class Tags:
    def __init__(self, tags_list=None, tags_dict=None, tags_file=None):
        """
        Assemble a Tags class
        """
        if sum(t is not None for t in [tags_list, tags_dict, tags_file]) > 1:
            click.echo(
                'Please specify only one of "tags_list", "tags_dict" or "tags_file"'
            )
            exit(1)

        self._tags_file = tags_file

        if tags_list:
            self._tags = list_to_dict(tags_list, 'Key', 'Value')
        elif tags_dict:
            self._tags = tags_dict
        else:
            self._tags = {}

    @property
    def string(self):
        return json.dumps(self.tags, sort_keys=True, indent=4)

    @property
    def tags(self):
        """
        Return dict tags
        """
        if self._tags_file:
            with open(self._tags_file) as fh:
                return json.load(fh)
        return self._tags

    def to_dict(self, extra_tags=None):
        if extra_tags:
            return {**self.tags, **extra_tags}
        return self._tags

    def to_list(self, extra_tags=None):
        if extra_tags:
            return dict_to_list({**self.tags, **extra_tags}, 'Key', 'Value')
        return dict_to_list(self.tags, 'Key', 'Value')
