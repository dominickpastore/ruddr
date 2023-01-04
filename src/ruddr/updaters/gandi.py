"""Ruddr updater for Gandi LiveDNS v5 API"""

import ipaddress
from json import JSONDecodeError
from pprint import pprint
from typing import Optional, Tuple, List, Union, cast

import requests

from ..configuration import USER_AGENT
from ..exceptions import ConfigError, PublishError
from .updater import TwoWayZoneUpdater


class GandiUpdater(TwoWayZoneUpdater):
    """Ruddr updater for Gandi LiveDNS v5 API

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param config: Dict of config options for this updater
    """

    def __init__(self, name, addrfile, config):
        super().__init__(name, addrfile, config['datadir'])

        # Validate FQDNs and store as list of (subdomain, domain) tuples
        try:
            fqdns = config['fqdns']
        except KeyError:
            self.log.critical("'fqdns' config option is required")
            raise ConfigError(f"{self.name} updater requires 'fqdns' config "
                              "option") from None
        self.init_hosts_and_zones(fqdns)

        # Gandi API key
        try:
            self.api_key = config['api_key']
        except KeyError:
            self.log.critical("'api_key' config option is required")
            raise ConfigError(f"{self.name} updater requires 'api_key' config "
                              "option") from None

        # Gandi API endpoint - base URL to use for the LiveDNS API. Normally
        # not required, but can be used if you wish to test in the sandbox
        # API environment
        self.endpoint = config.get('endpoint',
                                   'https://api.gandi.net/v5/livedns')

    def _api_request(self, method, api, params=None, data=None):
        """Issue a LiveDNS API request.

        :param method: HTTP method, ``'GET'`` or ``'PUT'``
        :param api: Specific API to access, e.g. ``'/dns/rrtypes'``
        :param params: A dict of URL parameters (i.e. the key=values that go
                       after the question mark in the URL)
        :param data: A JSON-serializable dict to become the request body.

        :return: The :class:`Response` object, or `None` if there was an error
                 (which will be logged)
        """
        headers = {'Authorization': "Apikey " + self.api_key,
                   'User-Agent': USER_AGENT}
        if method == 'GET':
            method_f = requests.get
        elif method == 'PUT':
            method_f = requests.put
        url = self.endpoint + api
        try:
            if params is None and data is None:
                r = method_f(url, headers=headers)
            elif params is None:
                r = method_f(url, headers=headers, json=data)
            elif data is None:
                r = method_f(url, headers=headers, params=params)
            else:
                r = method_f(url, headers=headers, params=params, json=data)
        except requests.exceptions.RequestException as e:
            self.log.error("Could not %s %s: %s", method, url, e)
            return None
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log.error("Received HTTP %d when trying to %s %s:\n%s",
                           r.status_code, method, url, r.text)
            return None

        try:
            obj = r.json()
        except JSONDecodeError:
            self.log.error("Could not parse JSON response from %s %s:\n%s",
                           method, url, r.text)
            return None
        return obj

    def get_zones(self):
        response = self._api_request('GET', '/domains')
        if response is None:
            raise PublishError("Could not fetch zones for updater "
                               f"{self.name}")
        try:
            result = [rec['fqdn'] for rec in response]
        except (KeyError, TypeError):
            self.log.error("Unknown response structure from /domains:\n%s",
                           pprint(response))
            raise PublishError("Unknown response structure from /domains")
        return result

    def _fetch_zone_records(self, zone: str, rec_type: str) -> Union[
        List[Tuple[str, ipaddress.IPv4Address, int]],
        List[Tuple[str, ipaddress.IPv6Address, int]],
    ]:
        """Fetch A or AAAA records for the given zone

        :param zone: The zone to fetch records for
        :param rec_type: ``'A'`` or ``'AAAA'``
        :return: A list of 3-tuples ``(subdomain, addr, ttl)`` as returned by
                 :meth:`fetch_zone_ipv4s` and :meth:`fetch_zone_ipv6s`
        """
        assert rec_type in ('A', 'AAAA')
        api = f'/domains/{zone}/records'
        params = {'rrset_type': rec_type}
        response = self._api_request('GET', api, params)
        if response is None:
            raise PublishError(f"Could not fetch {rec_type} records for zone "
                               f"'{zone}'")

        result: Union[
            List[Tuple[str, ipaddress.IPv4Address, int]],
            List[Tuple[str, ipaddress.IPv6Address, int]],
        ] = []

        try:
            for rec in response:
                name = rec['rrset_name']
                if name == '@':
                    name = ''
                ttl = rec['rrset_ttl']
                for ip in rec['rrset_values']:
                    if rec_type == 'A':
                        ip = ipaddress.IPv4Address(ip)
                    else:
                        ip = ipaddress.IPv6Address(ip)
                    result.append((name, ip, ttl))
        except ipaddress.AddressValueError:
            self.log.error("Invalid IP from %s:\n%s", api, pprint(response))
            raise PublishError(f"Invalid IP from {api}")
        except (KeyError, TypeError):
            self.log.error("Unknown response structure from %s:\n%s",
                           api, pprint(response))
            raise PublishError(f"Unknown response structure from {api}")
        return result

    def fetch_zone_ipv4s(
        self,
        zone: str
    ) -> List[Tuple[str, ipaddress.IPv4Address, Optional[int]]]:
        return cast(List[Tuple[str, ipaddress.IPv4Address, int]],
                    self._fetch_zone_records(zone, 'A'))

    def fetch_zone_ipv6s(
        self,
        zone: str
    ) -> List[Tuple[str, ipaddress.IPv6Address, Optional[int]]]:
        return cast(List[Tuple[str, ipaddress.IPv6Address, int]],
                    self._fetch_zone_records(zone, 'AAAA'))

    def _put_record(self, zone: str, subdomain: str,
                    rec_type: str, addrs: List[str], ttl: int):
        if subdomain == '':
            subdomain = '@'
        api = f'/domains/{zone}/records/{subdomain}/{rec_type}'
        data = {'rrset_values': addrs, 'rrset_ttl': ttl}
        response = self._api_request('PUT', api, data=data)
        if response is None:
            raise PublishError(f"Could not PUT {api}")

    def put_subdomain_ipv4(self, subdomain: str, zone: str,
                           address: ipaddress.IPv4Address, ttl: Optional[int]):
        assert ttl is not None
        addrs = [address.exploded]
        self._put_record(zone, subdomain, 'A', addrs, ttl)

    def put_subdomain_ipv6s(self, subdomain: str, zone: str,
                            addresses: List[ipaddress.IPv6Address],
                            ttl: Optional[int]):
        assert ttl is not None
        addrs = [address.compressed for address in addresses]
        self._put_record(zone, subdomain, 'AAAA', addrs, ttl)
