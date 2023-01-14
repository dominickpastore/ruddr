"""Ruddr updater for Duck DNS (duckdns.org)"""

import ipaddress
from typing import Dict

import requests

from .. import Addrfile
from ..configuration import USER_AGENT
from ..exceptions import ConfigError, PublishError
from .updater import OneWayUpdater


class DuckDNSUpdater(OneWayUpdater):
    """Ruddr updater for Duck DNS (duckdns.org)

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param config: Dict of config options for this updater
    """

    def __init__(self, name: str, addrfile: Addrfile, config: Dict[str, str]):
        super().__init__(name, addrfile)

        # Hosts
        try:
            hosts = config['hosts']
        except KeyError:
            self.log.critical("'hosts' config option is required")
            raise ConfigError(f"{self.name} updater requires 'hosts' config "
                              "option") from None
        hosts = [(h, f'{h}.duckdns.org') for h in hosts.split()]

        # Nameserver
        nameserver = config.get('nameserver', 'ns1.duckdns.org')
        if nameserver == '':
            self.log.debug("'nameserver' was empty. Using system DNS")
            nameserver = None

        self.init_params(hosts, nameserver)

        # Token
        try:
            self.token = config['token']
        except KeyError:
            self.log.critical("'token' config option is required")
            raise ConfigError(f"{self.name} updater requires 'token' config "
                              "option") from None

    def publish_ipv4_one_host(self,
                              hostname: str,
                              address: ipaddress.IPv4Address):
        self._send_request(hostname, 'ip', address.exploded)

    def publish_ipv6_one_host(self,
                              hostname: str,
                              address: ipaddress.IPv6Address):
        self._send_request(hostname, 'ipv6', address.compressed)

    def _send_request(self,
                      hostname: str,
                      addr_param: str,
                      addr: str):
        """Send a single update and handle the reply

        :param hostname: The host to update
        :param addr_param: The name of the address param, ``ip`` or ``ipv6``
        :param addr: The address to update with

        :raises PublishError: if the update fails
        """
        try:
            response = requests.get('https://www.duckdns.org/update',
                                    params={
                                        'domains': hostname,
                                        'token': self.token,
                                        addr_param: addr,
                                    },
                                    headers={'User-Agent': USER_AGENT})
        except requests.exceptions.RequestException as e:
            self.log.error("Could not update hostname '%s' to %s: %s",
                           hostname, addr, e)
            raise PublishError(f"Updater {self.name} could not update "
                               f"'{hostname}' to {addr}") from e

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log.error("Received HTTP %d when trying to update '%s' to "
                           "%s:\n%s", response.status_code, hostname, addr,
                           response.text)
            raise PublishError(f"Updater {self.name} got HTTP "
                               f"{response.status_code} when trying to update "
                               f"'{hostname}' to {addr}")

        if response.text.startswith('KO'):
            self.log.error("Received error when trying to update '%s' to %s",
                           hostname, addr)
            raise PublishError(f"Updater {self.name} received error when "
                               f"trying to update '{hostname}' to {addr}")
        elif response.text.startswith('OK'):
            self.log.info("Updated address for '%s' to %s", hostname, addr)
        else:
            self.log.error("Unexpected response when trying to update '%s' to "
                           "%s:\n%s", hostname, addr, response.text)
            raise PublishError(f"Updater {self.name} got unexpected response "
                               f"when trying to update '{hostname}' to {addr}")
