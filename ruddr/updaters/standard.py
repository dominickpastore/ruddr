"""Ruddr updater for the IPv4 address at Hurricane Electric's tunnel broker"""

import enum
import ipaddress
import socket
from typing import List, Optional, Tuple, Union, Dict

import dns.resolver
import requests

from ..configuration import USER_AGENT
from ..exceptions import ConfigError, PublishError, FatalPublishError
from .updater import Updater


class _IPv6Dialect(enum.Enum):
    SEPARATE = "separate"
    SEPARATE_NO = "separate_no"
    COMBINED = "combined"


class StandardUpdater(Updater):
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
            super().__init__(name, addrfile)
            self.log.critical("'min_retry_interval' config option must be an "
                              "integer")
            raise ConfigError(f"{name} updater requires an integer for "
                              "'min_retry_interval' config option")

        super().__init__(name, addrfile, min_retry)

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

        # Hosts
        try:
            hosts = config['hosts']
        except KeyError:
            self.log.critical("'hosts' config option is required")
            raise ConfigError(f"{self.name} updater requires 'hosts' config "
                              "option") from None
        self.hosts = self._split_hosts(hosts)

        # Nameserver
        self.nameserver = config.get('nameserver')

        # IPv6 dialect
        ipv6_dialect = config.get('ipv6_dialect', 'separate')
        try:
            self.ipv6_dialect = _IPv6Dialect(ipv6_dialect)
        except ValueError:
            self.log.critical(f"IPv6 dialect '{ipv6_dialect}' is not a valid "
                              "choice")
            raise ConfigError(f"{self.name} updater has invalid IPv6 dialect "
                              f"{ipv6_dialect}") from None

    def _split_hosts(
            self,
            hosts: str
    ) -> List[Tuple[str, Optional[Union[ipaddress.IPv6Address, str]]]]:
        """Split a hosts string into a list of (hostname,
        None|IPv6Address|hostname)"""
        hosts = hosts.split()
        result = []
        for host in hosts:
            hostname, sep, ip_lookup = host.partition("/")
            if sep == '':
                self.log.critical("'%s' entry in hosts needs an fqdn, IPv6, "
                                  "or '-' after a slash", hostname)
                raise ConfigError(f"{self.name} updater hosts entry {hostname}"
                                  " needs an fqdn, IPv6, or '-' after a slash")

            if hostname in [x[0] for x in result]:
                self.log.critical("'%s' entry in hosts is a duplicate")
                raise ConfigError(f"{self.name} updater has duplicate hosts "
                                  f"entry {hostname}")

            if ip_lookup == '-':
                result.append((hostname, None))
                continue

            try:
                ip_lookup = ipaddress.IPv6Address(ip_lookup)
            except ipaddress.AddressValueError as e:
                self.log.info("hosts entry '/%s' is not an IPv6 address; "
                              "treating as an fqdn", ip_lookup)

            # If ip_lookup was not converted to an IPv6Address, assume it's an
            # FQDN
            result.append((hostname, ip_lookup))

        return result

    def publish_ipv4(self, address):
        error = None
        for host, _ in self.hosts:
            try:
                self._publish_ipv4_one_host(host, address)
            except PublishError as e:
                if error is None:
                    error = e
        if error is not None:
            raise error

    def _publish_ipv4_one_host(self,
                               hostname: str,
                               address: ipaddress.IPv4Address):
        params = {'hostname': hostname}
        if self.ipv6_dialect is _IPv6Dialect.SEPARATE_NO:
            params['myip'] = address.exploded
            params['myipv6'] = 'no'
        else:
            params['myip'] = address.exploded

        self._send_request(params, hostname, 'IPv4', address.exploded)

    def publish_ipv6(self, network):
        error = None
        for host, ip_lookup in self.hosts:
            try:
                self._publish_ipv6_one_host(host, network, ip_lookup)
            except PublishError as e:
                if error is None:
                    error = e
        if error is not None:
            raise error

    def _publish_ipv6_one_host(
        self,
        hostname: str,
        network: ipaddress.IPv6Network,
        ip_lookup: Union[str, ipaddress.IPv6Address, None]
    ):
        if ip_lookup is None:
            return
        elif isinstance(ip_lookup, ipaddress.IPv6Address):
            current_ipv6 = ip_lookup
        else:
            try:
                current_ipv6 = self._lookup_ipv6(ip_lookup)
            except (OSError, dns.exception.DNSException) as e:
                self.log.error("Could not look up the current IPv6 address "
                               "for hostname %s: %s", hostname, e)
                raise PublishError(f"Updater {self.name} could not look up "
                                   "the current IPv6 address for hostname "
                                   f"{ip_lookup}")
            self.log.debug("Looked up IPv6 addr %s for hostname %s",
                           current_ipv6.compressed, hostname)
        new_ipv6 = self.replace_ipv6_prefix(network, current_ipv6)

        params = {'hostname': hostname}
        if self.ipv6_dialect is _IPv6Dialect.SEPARATE_NO:
            params['myip'] = 'no'
            params['myipv6'] = new_ipv6.compressed
        elif self.ipv6_dialect is _IPv6Dialect.COMBINED:
            params['myip'] = new_ipv6.compressed
        else:
            params['myipv6'] = new_ipv6.compressed

        self._send_request(params, hostname, 'IPv6', new_ipv6.compressed)

    def _lookup_ipv6(self, ip_lookup: str) -> Optional[ipaddress.IPv6Address]:
        """Do a DNS lookup for an AAAA record, preferring globally-routable
        addresses if multiple are present

        :raises OSError: if lookup failed
        :raises dns.exception.DNSException: if lookup failed
        :return: An :class:`~ipaddress.IPv6Address` or ``None`` if none could
                 be found
        """
        if self.nameserver is None:
            self.log.debug("Looking up AAAA record(s) for '%s' in system DNS",
                           ip_lookup)
            results = socket.getaddrinfo(ip_lookup, None,
                                         family=socket.AF_INET6)
            aaaa_records = [
                ipaddress.IPv6Address(ai[4][0]) for ai in results
            ]
        else:
            self.log.debug("Looking up address of nameserver %s",
                           self.nameserver)
            ns_results = socket.getaddrinfo(self.nameserver, 53,
                                            type=socket.SOCK_DGRAM)
            ns_list = [ai[4][0] for ai in ns_results]
            self.log.debug("Found address(es) for nameserver %s: %s",
                           self.nameserver, str(ns_list))

            self.log.debug("Looking up AAAA record(s) for '%s' on that "
                           "nameserver", ip_lookup)
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = ns_list
            answer = resolver.resolve(ip_lookup, 'AAAA')
            aaaa_records = [
                ipaddress.IPv6Address(rec.address)
                for rec in answer
            ]

        self.log.debug("Found following address(es) for %s: %s", ip_lookup,
                       str([addr.compressed for addr in aaaa_records]))

        # Sift through the addresses to find the first globally routable, or if
        # none, the first private, or if none, the first link-local address
        first_private = None
        first_link_local = None
        for addr in aaaa_records:
            if addr.is_global:
                return addr
            elif addr.is_link_local:
                if first_link_local is None:
                    first_link_local = addr
            elif addr.is_private:
                if first_private is None:
                    first_private = addr
        if first_private is not None:
            return first_private
        return first_link_local

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
                             headers={'user-agent': USER_AGENT})
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
