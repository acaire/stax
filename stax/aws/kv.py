"""
Common Cloudformation KeyValues
"""

import json


class KeyValue:
    """
    KeyValue class
    """
    def __init__(self, *args, list_fields, filename=None, values=None):
        if args or values and filename:
            raise ValueError('You must specify either values or filename')

        self.list_key_name, self.list_value_name = list_fields
        self.filename = filename
        self.values = values

    @property
    def values(self):
        """
        Return Tags values
        """
        return self.__values

    @values.setter
    def values(self, values):
        """
        Assign values from dict, list
        or JSON file as dict
        """
        if isinstance(values, dict):
            self.__values = values
        elif isinstance(values, list):
            self.__values = {
                value[self.list_key_name]: value[self.list_value_name]
                for value in values
            }
        elif self.filename:
            with open(self.filename) as fh:
                self.__values = json.load(fh)
        elif values is None:
            self.__values = dict()
        else:
            raise ValueError('Values passed must be a dict or list')

    @property
    def to_dict(self):
        """
        Return a dictionary of Cloudformation Parameters
        """
        return self.values

    @property
    def to_list(self):
        """
        Return a list of Cloudformation Parameters
        """
        return [{
            self.list_key_name: k,
            self.list_value_name: v
        } for k, v in self.to_dict.items()]
