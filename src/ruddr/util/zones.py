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

"""Tools for splitting a domain into subdomain part and zone part"""

import os
import os.path
from typing import Tuple, Optional
import sys
if sys.version_info < (3, 8):
    from typing_extensions import Protocol
else:
    from typing import Protocol

import tldextract


class _TLDExtractor(Protocol):
    def __call__(
        self, url: str, include_psl_private_domains: Optional[bool] = ...
    ) -> tldextract.tldextract.ExtractResult:
        ...


class ZoneSplitter:
    """A utility to split domains into subdomain part and zone part using the
    `Public Suffix List`_

    .. _Public Suffix List: https://publicsuffix.org/

    :param datadir: The data directory configured for Ruddr
    :raises OSError: if the public suffix list could not be fetched due to I/O
                     issues (cache directory could not be created, could not
                     connect to server, etc.)
    """

    def __init__(self, datadir: str):
        self._tld_cache_dir: str = os.path.join(datadir, 'tldextract')
        os.makedirs(os.path.dirname(self._tld_cache_dir), exist_ok=True)
        self._extract_func: _TLDExtractor = tldextract.TLDExtract(
            cache_dir=self._tld_cache_dir,
            include_psl_private_domains=True,
        )

    def split(self, domain: str) -> Tuple[str, str]:
        """Split a domain name into subdomain part and zone part

        :param domain: The FQDN to split
        :return: A tuple with the two parts. The subdomain part may be empty if
                 the FQDN was the root domain of its zone.
        """
        subdomain, domain, suffix = self._extract_func(domain)
        zone = '.'.join(part for part in (domain, suffix) if part != '')
        return (subdomain, zone)
