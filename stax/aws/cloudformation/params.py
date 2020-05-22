"""
AWS Cloudformation Params
"""

from stax.aws.kv import KeyValue


class Params(KeyValue):
    def __init__(self, **kwargs):
        super().__init__(**kwargs,
                         list_fields=('ParameterKey', 'ParameterValue'))

    @property
    def to_list_with_previous_values(self):
        """
        Return a list of Cloudformation Parameters
        Although remove the values, and set UsePreviousValue
        """
        return [{
            self.list_key_name: k,
            'UsePreviousValue': True,
        } for k, v in self.to_dict.items()]
