from unittest import mock

import pytest

from stax.aws.kv import KeyValue


def test_both_supplied():
    with pytest.raises(ValueError,
                       match='You must specify either values or filename'):
        KeyValue(values={'key': 'value'},
                 filename='dummy.json',
                 list_fields=('one', 'two'))


def test_dict():
    valid_dict = {'key': 'value'}
    key_values = KeyValue(values=valid_dict, list_fields=('one', 'two'))
    assert key_values.to_dict == valid_dict


def test_dict_none():
    key_values = KeyValue(values=None, list_fields=('one', 'two'))


def test_dict_invalid():
    invalid_dict = 'invalid'
    with pytest.raises(ValueError,
                       match=r'^Values passed must be a dict or list$'):
        KeyValue(values=invalid_dict, list_fields=('one', 'two'))


def test_list():
    valid_list = [{'one': 'key', 'two': 'value'}]
    key_values = KeyValue(values=valid_list, list_fields=('one', 'two'))
    assert key_values.to_list == valid_list


@mock.patch('builtins.open', mock.MagicMock())
@mock.patch('json.load', mock.MagicMock(side_effect=[{'key': 'value'}]))
def test_filename():
    assert KeyValue(filename='/tmp/dummy_file',
                    list_fields=('one', 'two')).values == {
                        'key': 'value'
                    }
