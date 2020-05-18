"""
Stax Exceptions
"""


class StaxException(Exception):
    """
    Generic Exception
    """
    pass


class StackNotFound(StaxException):
    """
    AWS Cloudformation Stack Not Found Exception
    """
    pass
