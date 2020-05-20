from stax.utils import plural


def test_singular():
    assert plural(1, "apple") == '1 apple'


def test_plural():
    assert plural(2, "apple") == '2 apples'


def test_singular_with_custom_plural():
    assert plural(1, "box", plural="boxes") == '1 box'


def test_plural_with_custom_plural():
    assert plural(0, "box", plural="boxes") == '0 boxes'
