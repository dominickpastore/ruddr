#  Ruddr - Robotic Updater for Dynamic DNS Records
#  Copyright (C) 2023 Dominick C. Pastore
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

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


class RequestsFamilyRestriction:
    """Context manager that causes Requests to only use the specified address
    family.

    For example, to force a request over IPv6::

        with RequestsFamilyRestriction(socket.AF_INET6):
            r = requests.get("https://icanhazip.com/")
        # error checking skipped
        ipv6 = r.text

    :param family: The address family to use (typically a ``socket.AF_*``
                   constant from Python's :mod:`socket` module)
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
