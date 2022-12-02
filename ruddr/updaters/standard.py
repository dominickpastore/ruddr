"""Ruddr updater for the IPv4 address at Hurricane Electric's tunnel broker"""

import enum
import ipaddress
from typing import Dict

import requests

from ..configuration import USER_AGENT
from ..exceptions import ConfigError, PublishError, FatalPublishError
from .updater import OneWayUpdater


class _IPv6Dialect(enum.Enum):
    SEPARATE = "separate"
    SEPARATE_NO = "separate_no"
    COMBINED = "combined"


class StandardUpdater(OneWayUpdater):
    """Ruddr updater for providers using the de facto standard /nic/update API

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param config: Dict of config options for this updater
    """

    def __init__(self, name, addrfile, config: dict):
        # Minimum retry interval
        try:
            min_retry = int(config.get('min_retry_interval', '300'))
        except ValueError:
            super().__init__(name, addrfile, [])
            self.log.critical("'min_retry_interval' config option must be an "
                              "integer")
            raise ConfigError(f"{name} updater requires an integer for "
                              "'min_retry_interval' config option")

        # Hosts
        try:
            hosts = config['hosts']
        except KeyError:
            super().__init__(name, addrfile, [])
            self.log.critical("'hosts' config option is required")
            raise ConfigError(f"{self.name} updater requires 'hosts' config "
                              "option") from None

        # Nameserver
        nameserver = config.get('nameserver')

        super().__init__(name, addrfile, hosts, nameserver, min_retry)

        # Endpoint
        try:
            self.endpoint = config['endpoint']
        except KeyError:
            self.log.critical("'endpoint' config option is required")
            raise ConfigError(f"{self.name} updater requires 'endpoint' config"
                              " option") from None
        if self.endpoint[-1] == '/':
            self.endpoint = self.endpoint[:-1]
        self.endpoint += "/nic/update"

        # Username
        try:
            username = config['username']
        except KeyError:
            self.log.critical("'username' config option is required")
            raise ConfigError(f"{self.name} updater requires 'username' config"
                              " option") from None

        # Password
        try:
            password = config['password']
        except KeyError:
            self.log.critical("'password' config option is required")
            raise ConfigError(f"{self.name} updater requires 'password' config"
                              " option") from None

        self.auth = (username, password)

        # IPv6 dialect
        ipv6_dialect = config.get('ipv6_dialect', 'separate')
        try:
            self.ipv6_dialect = _IPv6Dialect(ipv6_dialect)
        except ValueError:
            self.log.critical(f"IPv6 dialect '{ipv6_dialect}' is not a valid "
                              "choice")
            raise ConfigError(f"{self.name} updater has invalid IPv6 dialect "
                              f"{ipv6_dialect}") from None

    def publish_ipv4_one_host(self,
                              hostname: str,
                              address: ipaddress.IPv4Address):
        """Attempt to publish an IPv4 address for a single host

        :param hostname: The host to publish for
        :param address: The address to publish

        :raise PublishError: if publishing fails
        :raise FatalPublishError: if publishing fails in a non-recoverable way
                                  (all future publishing will halt)
        """
        params = {'hostname': hostname}
        if self.ipv6_dialect is _IPv6Dialect.SEPARATE_NO:
            params['myip'] = address.exploded
            params['myipv6'] = 'no'
        else:
            params['myip'] = address.exploded

        self._send_request(params, hostname, 'IPv4', address.exploded)

    def publish_ipv6_one_host(
        self,
        hostname: str,
        address: ipaddress.IPv6Address
    ):
        """Attempt to publish an IPv6 address for a single host

        :param hostname: The host to publish for
        :param address: The address to publish

        :raise PublishError: if publishing fails
        :raise FatalPublishError: if publishing fails in a non-recoverable way
                                  (all future publishing will halt)
        """
        params = {'hostname': hostname}
        if self.ipv6_dialect is _IPv6Dialect.SEPARATE_NO:
            params['myip'] = 'no'
            params['myipv6'] = address.compressed
        elif self.ipv6_dialect is _IPv6Dialect.COMBINED:
            params['myip'] = address.compressed
        else:
            params['myipv6'] = address.compressed

        self._send_request(params, hostname, 'IPv6', address.compressed)

    def _send_request(self,
                      params: Dict[str, str],
                      hostname: str,
                      addr_type: str,
                      addr: str):
        """Send an update request and handle the reply

        :param params: Dict of parameters to send with the request
        :param addr_type: ``'IPv4'`` or ``'IPv6'``
        """
        try:
            r = requests.get(self.endpoint,
                             auth=self.auth,
                             params=params,
                             headers={'User-Agent': USER_AGENT})
        except requests.exceptions.RequestException as e:
            self.log.error("Could not update hostname '%s' %s to %s: %s",
                           hostname, addr_type, addr, e)
            raise PublishError("Updater %s could not access %s: %s" % (
                self.name, self.endpoint, e)) from e

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log.error("Received HTTP %d when trying to update hostname "
                           "'%s' %s to %s:\n%s", r.status_code,
                           hostname, addr_type, addr, r.text)
            raise PublishError("Updater %s got HTTP %d for %s" % (
                self.name, r.status_code, self.endpoint)) from e

        response = r.text.strip().split()
        if response[0] == 'good':
            self.log.info("Hostname '%s' %s updated to %s",
                          hostname, addr_type, addr)
            return
        if response[0] == 'nochg':
            self.log.info("Hostname '%s' %s already set to %s",
                          hostname, addr_type, addr)
            return
        # Different providers have different error codes. The following are for
        # server-side issues at various providers, indicating a retry is
        # reasonable.
        if response[0] in ('911', 'dnserr', 'servererror'):
            self.log.error("Server returned response '%s' when trying to "
                           "update hostname '%s' %s to %s",
                           r.text, hostname, addr_type, addr)
            raise PublishError("Updater %s got response from server: %s" %
                               (self.name, r.text))
        # Other return codes are likely client-side issues (e.g. bad config,
        # agent is blocked). Do not retry.
        else:
            self.log.error("Server returned response '%s' when trying to "
                           "update hostname '%s' %s to %s",
                           r.text, hostname, addr_type, addr)
            raise FatalPublishError("Updater %s got response from server: %s" %
                                    (self.name, r.text))
