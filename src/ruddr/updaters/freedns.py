"""Ruddr updater for freedns.afraid.org"""
import hashlib
import ipaddress
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import requests

from .. import Addrfile
from ..configuration import USER_AGENT
from ..exceptions import ConfigError, PublishError
from .updater import TwoWayUpdater


@dataclass
class _SubdomainRecord:
    url4: Optional[str] = None
    url6: Optional[str] = None
    ipv4: Optional[ipaddress.IPv4Address] = None
    ipv6: Optional[ipaddress.IPv6Address] = None


class FreeDNSUpdater(TwoWayUpdater):
    """Ruddr updater for freedns.afraid.org

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param config: Dict of config options for this updater
    """

    def __init__(self, name: str, addrfile: Addrfile, config: Dict[str, str]):
        super().__init__(name, addrfile, config['datadir'])

        # Username and password
        try:
            username = config['username']
        except KeyError:
            self.log.critical("'username' config option is required")
            raise ConfigError(f"{self.name} updater requires 'username' "
                              "config option") from None
        try:
            password = config['password']
        except KeyError:
            self.log.critical("'password' config option is required")
            raise ConfigError(f"{self.name} updater requires 'password' "
                              "config option") from None
        auth_string = username.lower() + '|' + password[:16]
        self.account_sha1 = hashlib.sha1(auth_string.encode()).hexdigest()

        # List of domains to update
        try:
            fqdns = config['fqdns']
        except KeyError:
            self.log.critical("'fqdns' config option is required")
            raise ConfigError(f"{self.name} updater requires 'fqdns' config "
                              "option") from None
        self.init_hosts(fqdns)

        #: Stores subdomain update URLs between when they are fetched and
        #: when they are put
        self._fetched_subdomains: Dict[str, _SubdomainRecord] = dict()

    def _get_account_subdomains(self) -> Dict[str, _SubdomainRecord]:
        """Fetch a list of the account's subdomains and return them in a dict

        :returns: A dict with subdomain names as keys and
                  :class:`_SubdomainRecord` as values
        :raises PublishError: If the list of subdomains could not be fetched
        """
        self.log.debug("Fetching account subdomains")
        try:
            response = requests.get("https://freedns.afraid.org/api/",
                                    params={
                                        'action': 'getdyndns',
                                        'v': '2',
                                        'sha': self.account_sha1
                                    },
                                    headers={'User-Agent': USER_AGENT})
        except requests.exceptions.RequestException as e:
            self.log.error("Could not get list of account subdomains: %s", e)
            raise PublishError("Could not get list of account subdomains")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log.error("Received HTTP %d when trying to get list of "
                           "account subdomains:\n%s",
                           response.status_code, response.text)
            raise PublishError(f"Received HTTP {response.status_code} when "
                               "trying to get list of account subdomains")

        # This API doesn't seem to return status codes other than 200, but
        # errors are always given as HTML

        if response.headers['content-type'].startswith('text/html'):
            self.log.error("Received abnormal response when trying to get list"
                           " of account subdomains:\n%s", response.text)
            raise PublishError("Received abnormal response when trying to get "
                               "list of account subdomains")

        result = dict()
        for line in response.text.splitlines():
            subdomain, addr, update_url = line.split('|', maxsplit=2)
            subdomain_record = result.setdefault(subdomain, _SubdomainRecord())
            try:
                ipv6 = ipaddress.IPv6Address(addr)
            except ValueError:
                subdomain_record.url4 = update_url
                subdomain_record.ipv4 = ipaddress.IPv4Address(addr)
            else:
                subdomain_record.url6 = update_url
                subdomain_record.ipv6 = ipv6
        return result

    def fetch_all_ipv4s(
            self
    ) -> List[Tuple[str, ipaddress.IPv4Address, Optional[int]]]:
        self._fetched_subdomains = self._get_account_subdomains()

        result = []
        for subdomain, record in self._fetched_subdomains.items():
            if record.ipv4 is not None:
                result.append((subdomain, record.ipv4, None))
        return result

    def fetch_all_ipv6s(
        self
    ) -> List[Tuple[str, ipaddress.IPv6Address, Optional[int]]]:
        self._fetched_subdomains = self._get_account_subdomains()

        result = []
        for subdomain, record in self._fetched_subdomains.items():
            if record.ipv6 is not None:
                result.append((subdomain, record.ipv6, None))
        return result

    def put_domain_ipv4(self, domain: str,
                        address: ipaddress.IPv4Address, ttl: Optional[int]):
        address = address.exploded
        url = self._fetched_subdomains[domain].url4
        self._update_one(domain, url, address)

    def put_domain_ipv6s(self, domain: str,
                         addresses: List[ipaddress.IPv6Address],
                         ttl: Optional[int]):
        if len(addresses) != 1:
            self.log.critical(f"There is a bug in freedns updater {self.name}:"
                              " Incorrect number of IPv6 addresses in "
                              f"put_domain_ipv6s: {addresses}")
            raise PublishError("Bug in freedns updater")
        address = addresses[0].compressed
        url = self._fetched_subdomains[domain].url6
        self._update_one(domain, url, address)

    def _update_one(self, fqdn: str, url: str, address: str):
        """Update a single domain's IP address

        :param fqdn: The domain to update
        :param url: The update URL
        :param address: The address to update with

        :raises PublishError: if not successful
        """
        self.log.debug("Updating IP address for %s to %s", fqdn, address)
        try:
            response = requests.get(url, params={'address': address},
                                    headers={'User-Agent': USER_AGENT})
        except requests.exceptions.RequestException as e:
            self.log.error("Could not update %s to %s: %s", fqdn, address, e)
            raise PublishError(f"Could not update {fqdn} to {address}")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log.error("Received HTTP %d when trying to update %s to %s:\n"
                           "%s", response.status_code, fqdn, address,
                           response.text)
            raise PublishError(f"Received HTTP {response.status_code} when "
                               f"trying to upcate {fqdn} to {address}")

        # This API seems to always return plain text. Errors are in the form
        # "ERROR: message" and successes in the form
        # "Updated <x> host(s) <fqdn> to <ip> in <y> seconds"

        if response.headers['content-type'].startswith('text/html'):
            self.log.error("Received abnormal response when trying to update"
                           "%s to %s:\n%s", fqdn, address, response.text)
            raise PublishError("Received abnormal response when trying to "
                               f"update {fqdn} to {address}")
        if response.text.startswith("ERROR:"):
            self.log.error("Received error when trying to update %s to %s:\n"
                           "%s", fqdn, address, response.text[7:])
            raise PublishError(f"Received error when trying to update {fqdn} "
                               f"to {address}")

        self.log.info("Updated address for %s to %s", fqdn, address)
