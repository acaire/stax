"""
AWS Cloudformation Params
"""

from stax.aws.kv import KeyValue


class Params(KeyValue):
    def __init__(self, **kwargs):
        super().__init__(**kwargs,
                         list_fields=('ParameterKey', 'ParameterValue'))
