"""
AWS Cloudformation Tags
"""

from stax.aws.kv import KeyValue


class Tags(KeyValue):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, list_fields=('Key', 'Value'))
