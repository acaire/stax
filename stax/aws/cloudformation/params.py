"""
AWS Cloudformation Params
"""

import json

from stax.utils import dict_to_list, list_to_dict


class Params:
    def __init__(self, params_list=None, params_dict=None, params_file=None):
        """
        Assemble a Paramsclass
        """
        if sum(t is not None
               for t in [params_list, params_dict, params_file]) > 1:
            click.echo(
                'Please specify only one of "params_list", "params_dict" or "params_file"'
            )
            exit(1)

        self._params_file = params_file

        if params_list:
            self._params = list_to_dict(params_list)
        elif params_dict:
            self._params = params_dict
        else:
            self._params = {}

    @property
    def string(self):
        return json.dumps(self.params, sort_keys=True, indent=4)

    @property
    def params(self):
        """
        Return params
        """
        if self._params_file:
            with open(self._params_file) as fh:
                return json.load(fh)
        return self._params

    def to_dict(self, extra_params=None):
        if extra_params:
            return {**self._params, **extra_params}
        return self._params

    def to_list(self, extra_params=None):
        if extra_params:
            return dict_to_list({
                **self.params,
                **extra_params
            }, 'ParamsKey', 'ParamsValue')
        return dict_to_list(self.params, 'ParamsKey', 'ParamsValue')
