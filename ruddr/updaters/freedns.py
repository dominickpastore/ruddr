"""Ruddr updater for freedns.afraid.org"""
import hashlib
import ipaddress
from dataclasses import dataclass
from typing import Dict, Optional

import requests

from .. import Addrfile
from ..configuration import USER_AGENT
from ..exceptions import ConfigError, PublishError
from .updater import Updater


@dataclass
class _SubdomainRecord:
    url4: Optional[str] = None
    url6: Optional[str] = None
    ipv6: Optional[ipaddress.IPv6Address] = None


class FreeDNSUpdater(Updater):
    """Ruddr updater for freedns.afraid.org

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param config: Dict of config options for this updater
    """

    def __init__(self, name: str, addrfile: Addrfile, config: Dict[str, str]):
        super().__init__(name, addrfile)

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
        self.fqdns = fqdns.split()

    def _get_account_subdomains(self) -> Optional[Dict[str, _SubdomainRecord]]:
        """Fetch a list of the account's subdomains and return them in a dict

        :returns: A dict with subdomain names as keys and
                  :class:`_SubdomainRecord` as values, or ``None`` if there is
                  an error
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
            return None

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log.error("Received HTTP %d when trying to get list of "
                           "account subdomains:\n%s",
                           response.status_code, response.text)
            return None

        # This API doesn't seem to return status codes other than 200, but
        # errors are always given as HTML

        if response.headers['content-type'].startswith('text/html'):
            self.log.error("Received abnormal response when trying to get list"
                           " of account subdomains:\n%s", response.text)
            return None

        result = dict()
        for line in response.text.splitlines():
            subdomain, addr, update_url = line.split('|', maxsplit=2)
            subdomain_record = result.setdefault(subdomain, _SubdomainRecord())
            try:
                ipv6 = ipaddress.IPv6Address(addr)
            except ValueError:
                subdomain_record.url4 = update_url
            else:
                subdomain_record.url6 = update_url
                subdomain_record.ipv6 = ipv6
        return result

    def publish_ipv4(self, address: ipaddress.IPv4Address):
        acct_fqdns = self._get_account_subdomains()
        if acct_fqdns is None:
            raise PublishError("Could not fetch account subdomains")

        success = True
        for fqdn in self.fqdns:
            try:
                record = acct_fqdns[fqdn]
            except KeyError:
                self.log.warning("Account does not have domain %s", fqdn)
                success = False
                continue
            if record.url4 is None:
                self.log.warning("Domain %s does not have IPv4 update URL "
                                 "(have you assigned an IPv4 yet?", fqdn)
                success = False
                continue
            if not self._update_one(fqdn, record.url4, address.exploded):
                success = False

        if not success:
            raise PublishError("Could not update all records")

    def publish_ipv6(self, network: ipaddress.IPv6Network):
        acct_fqdns = self._get_account_subdomains()
        if acct_fqdns is None:
            raise PublishError("Could not fetch account subdomains")

        success = True
        for fqdn in self.fqdns:
            try:
                record = acct_fqdns[fqdn]
            except KeyError:
                self.log.warning("Account does not have domain %s", fqdn)
                success = False
                continue
            if record.url6 is None:
                self.log.warning("Domain %s does not have IPv4 update URL "
                                 "(have you assigned an IPv4 yet?", fqdn)
                success = False
                continue
            new_ipv6 = self.replace_ipv6_prefix(network, record.ipv6)
            if not self._update_one(fqdn, record.url6, new_ipv6.compressed):
                success = False

        if not success:
            raise PublishError("Could not update all records")

    def _update_one(self, fqdn: str, url: str, address: str):
        """Update a single domain's IP address

        :param fqdn: The domain to update
        :param url: The update URL
        :param address: The address to update with

        :returns: ``True`` if successful, ``False`` if not
        """
        self.log.debug("Updating IP address for %s to %s", fqdn, address)
        try:
            response = requests.get(url, params={'address': address},
                                    headers={'User-Agent': USER_AGENT})
        except requests.exceptions.RequestException as e:
            self.log.error("Could not update %s to %s: %s", fqdn, address, e)
            return False

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log.error("Received HTTP %d when trying to update %s to %s:\n"
                           "%s", response.status_code, fqdn, address,
                           response.text)
            return False
            
        # This API seems to always return plain text. Errors are in the form
        # "ERROR: message" and successes in the form
        # "Updated <x> host(s) <fqdn> to <ip> in <y> seconds"

        if response.headers['content-type'].startswith('text/html'):
            self.log.error("Received abnormal response when trying to update"
                           "%s to %s:\n%s",fqdn, address, response.text)
            return False
        if response.text.startswith("ERROR:"):
            self.log.error("Received error when trying to update %s to %s:\n"
                           "%s", fqdn, address, response.text[7:])
            return False

        self.log.info("Updated address for %s to %s", fqdn, address)
        return True
