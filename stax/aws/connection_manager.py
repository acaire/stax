"""
AWS Connection Manager
"""

import boto3

_CLIENTS = {}
_SESSIONS = {}


def get_client(profile, region, client):
    """
    Fetch an AWS Client, and store it
    incase it needs to be used again
    """
    client_key = (profile, region, client)
    session_key = profile

    if client_key not in _CLIENTS:
        if session_key not in _SESSIONS:
            _SESSIONS[session_key] = boto3.Session(profile_name=profile)
        _CLIENTS[client_key] = _SESSIONS[session_key].client(
            client, region_name=region)
    return _CLIENTS[client_key]
