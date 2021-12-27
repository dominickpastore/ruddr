"""Monkey patch Requests/Urllib3 to allow restricting the address family"""

import threading
from requests.packages.urllib3.util import connection

_allowed_gai_family_orig = connection.allowed_gai_family

_allowed_family_mutex = threading.RLock()
_allowed_family = None

def _allowed_gai_family():
    with _allowed_family_mutex:
        if _allowed_family is None:
            return _allowed_gai_family_orig()
        else:
            return _allowed_family

connection.allowed_gai_family = _allowed_gai_family

class FamilyRestriction:
    """Context manager that causes Urllib3/Requests to only use the specified
    address family

    :param family: The address family to use
    """

    def __init__(self, family):
        self.family = family

    def __enter__(self):
        global _allowed_family
        _allowed_family_mutex.acquire()
        _allowed_family = self.family

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _allowed_family
        _allowed_family = None
        _allowed_family_mutex.release()
