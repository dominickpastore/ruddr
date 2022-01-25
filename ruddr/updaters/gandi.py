"""Ruddr updater for Gandi LiveDNS v5 API"""

import ipaddress
from json import JSONDecodeError
from pprint import pprint
import re
import requests

from ..exceptions import ConfigError, PublishError
from .updater import Updater


class GandiUpdater(Updater):
    """Ruddr updater for Gandi LiveDNS v5 API

    :param name: Name of the updater (from config section heading)
    :param manager: The DDNSManager
    :param config: Dict of config options for this updater
    """

    # Regex for checking whether a domain "part" (i.e. one of the portions
    # delimited by dots) is valid
    _fqdn_part_re = re.compile('[A-Za-z]([-A-Za-z0-9]*[A-Za-z0-9])?')

    def __init__(self, name, manager, config):
        super().__init__(name, manager, config)

        # Validate FQDNs and store as list of (subdomain, domain) tuples
        try:
            fqdns = config['fqdns']
        except KeyError:
            self.log.critical("'fqdns' config option is required")
            raise ConfigError(f"{self.name} updater requires 'fqdns' config "
                              "option") from None
        fqdns = fqdns.split()
        self.fqdns = [self._split_fqdn(fqdn) for fqdn in fqdns]

        # Gandi API key
        try:
            self.api_key = config['api_key']
        except KeyError:
            self.log.critical("'api_key' config option is required")
            raise ConfigError(f"{self.name} updater requires 'api_key' config "
                              "option") from None

        # Gandi API endpoint - base URL to use for the LiveDNS API. Normally
        # not required, but can be used if Gandi provides a staging API
        # environment (they currently do not, as of Sep. 16, 2021)
        self.endpoint = config.get('endpoint',
                                   'https://api.gandi.net/v5/livedns')

    def _split_fqdn(self, fqdn):
        """Split a FQDN into domain and subdomain

        :param fqdn: Fully-qualified domain name, with or without trailing dot

        :return: A 2-tuple ``(subdomain, domain)``
        """
        parts = fqdn.split('.')
        if parts[-1] == '':
            del parts[-1]

        # Validate the parts
        if parts[0] == '':
            self.log.critical('FQDN "%s" is invalid.', fqdn)
            raise ConfigError('FQDN "%s" is invalid.' % fqdn)
        for part in parts:
            if self._fqdn_part_re.fullmatch(part) is None:
                self.log.critical('FQDN "%s" is invalid.', fqdn)
                raise ConfigError('FQDN "%s" is invalid.' % fqdn)

        if len(parts) < 2:
            self.log.critical('FQDN "%s" is invalid.', fqdn)
            raise ConfigError('FQDN "%s" is invalid.' % fqdn)
        if len(parts) == 2:
            return ('@', '.'.join(parts))
        return ('.'.join(parts[:-2]), '.'.join(parts[-2:]))

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
        headers = {'Authorization': "Apikey " + self.api_key}
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
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            self.log.error("Received HTTP %d when trying to %s %s:\n%s",
                           r.status_code, method, url, r.text)
            return None
        except requests.exceptions.RequestException as e:
            self.log.error("Could not %s %s: %s", method, url, e)
            return None

        try:
            obj = r.json()
        except JSONDecodeError:
            self.log.error("Could not parse JSON response from %s %s:\n%s",
                           method, url, r.text)
            return None
        return obj

    def get_zones(self):
        """Get a list of domain names for which Gandi maintains zones.

        :return: The list of domain names
        :raises PublishError: if could not fetch zones
        """
        api = '/domains'
        response = self._api_request('GET', api)
        if response is None:
            raise PublishError("Could not fetch zones for updater %s" %
                               self.name)
        try:
            result = [rec['fqdn'] for rec in response]
        except (KeyError, TypeError):
            self.log.error("Unknown response structure from %s %s:\n%s",
                           'GET', api, pprint(response))
            raise PublishError("Could not fetch zones for updater %s" %
                               self.name)
        return result

    def get_a_records(self, zone):
        """Get a dict of all the A records for this domain, where keys are
        subdomain names (or ``'@'`` for the domain itself) and values are lists
        of IPv4 addresses.

        :param zone: The domain name whose zone to fetch records from

        :return: The dict mapping subdomains to lists of :class:`IPv4Address`
        """
        api = f'/domains/{zone}/records'
        params = {'rrset_type': 'A'}
        response = self._api_request('GET', api, params)
        if response is None:
            return None

        result = dict()
        try:
            for rec in response:
                ips = [ipaddress.IPv4Address(ip) for ip in rec['rrset_values']]
                result[rec['rrset_name']] = ips
        except ipaddress.AddressValueError:
            self.log.error("Invalid IPv4 from %s %s:\n%s",
                           'GET', api, pprint(response))
            return None
        except (KeyError, TypeError):
            self.log.error("Unknown response structure from %s %s:\n%s",
                           'GET', api, pprint(response))
            return None
        return result

    def get_aaaa_records(self, zone):
        """Get a dict of all the AAAA records for this domain, where keys are
        subdomain names (or ``'@'`` for the domain itself) and values are lists
        of IPv6 addresses.

        :param zone: The domain name whose zone to fetch records from

        :return: The dict mapping subdomains to lists of :class:`IPv6Address`
        """
        api = f'/domains/{zone}/records'
        params = {'rrset_type': 'AAAA'}
        response = self._api_request('GET', api, params)
        if response is None:
            return None

        result = dict()
        try:
            for rec in response:
                ips = [ipaddress.IPv6Address(ip) for ip in rec['rrset_values']]
                result[rec['rrset_name']] = ips
        except ipaddress.AddressValueError:
            self.log.error("Invalid IPv6 from %s %s:\n%s",
                           'GET', api, pprint(response))
            return None
        except (KeyError, TypeError):
            self.log.error("Unknown response structure from %s %s:\n%s",
                           'GET', api, pprint(response))
            return None
        return result

    def put_a_record(self, zone, name, ip):
        """Create or replace the A records for the given domain and subdomain
        (``'@'`` for the domain itself) with a single A record for the given IP
        address.

        :param zone: The domain name whose zone to fetch records from
        :param name: The subdomain to set the A record for
        :param ip: An :class:`IPv4Address` to use for the A record

        :return: `True` if successful, `False` and logs errors if unsuccessful
        """
        api = f'/domains/{zone}/records/{name}/A'
        data = {'rrset_values': [ip.exploded], 'rrset_ttl': 1800}
        response = self._api_request('PUT', api, data=data)
        if response is None:
            return False
        self.log.info("Updated IPv4 for %s.%s to %s", name, zone, ip.exploded)
        return True

    def put_aaaa_records(self, zone, name, ip_list):
        """Create or replace the AAAA records for the given domain and
        subdomain (``'@'`` for the domain itself) with a new set of AAAA
        records for the given IP addresses.

        :param zone: The domain name whose zone to fetch records from
        :param name: The subdomain to set AAAA records for
        :param ip_list: A list of :class:`IPv6Address` to use for the AAAA
                        records

        :return: `True` if successful, `False` and logs errors if unsuccessful
        """
        api = f'/domains/{zone}/records/{name}/AAAA'
        ip_list = [ip.compressed for ip in ip_list]
        data = {'rrset_values': ip_list, 'rrset_ttl': 1800}
        response = self._api_request('PUT', api, data=data)
        if response is None:
            return False
        self.log.info("Updated IPv6s for %s.%s to %s", name, zone,
                      [ip.compressed for ip in ip_list])
        return True

    def _get_subdomain_zones(self):
        """Get a dict mapping each zone in LiveDNS to the corresponding
        subdomains configured for updates. (Only checks if the zone exists, not
        if the subdomains are part of it.)

        Warnings will be logged for any subdomain that's not part of a zone
        in LiveDNS, and that zone's value in the dict will be None.
        """
        domains = self.get_zones()
        result = dict()
        for subdomain, domain in self.fqdns:
            if domain not in domains:
                self.log.warning("Domain name %s is not an available zone.",
                                 domain)
                result[domain] = None
                continue
            try:
                result[domain].append(subdomain)
            except KeyError:
                result[domain] = [subdomain]
        return result

    def publish_ipv4(self, address):
        zone_subdomains = self._get_subdomain_zones()

        success = True
        for zone, subdomains in zone_subdomains.items():
            if subdomains is None:
                # self._get_subdomain_zones() logged about the missing zone
                success = False
                continue

            a_records = self.get_a_records(zone)
            if a_records is None:
                success = False
                continue

            for subdomain in subdomains:
                if subdomain not in a_records:
                    self.log.warning("Subdomain %s does not have A records in "
                                     "zone %s.", subdomain, zone)
                    success = False
                    continue
                if a_records[subdomain] == [address]:
                    self.log.info("Subdomain %s in zone %s already has address"
                                  " %s. Skipping.", subdomain, zone,
                                  address.exploded)
                    continue
                if not self.put_a_record(zone, subdomain, address):
                    success = False

        if not success:
            raise PublishError("Could not update all records")

    @staticmethod
    def replace_prefix(net6, addr6):
        """Replace the prefix portion of the given IPv6 address with the network
        prefix provided and return the result"""
        host = int(addr6) & ((1 << net6.prefixlen) - 1)
        return net6[host]

    def publish_ipv6(self, network):
        zone_subdomains = self._get_subdomain_zones()

        success = True
        for zone, subdomains in zone_subdomains.items():
            if subdomains is None:
                # self._get_subdomain_zones() logged about the missing zone
                success = False
                continue

            aaaa_records = self.get_aaaa_records(zone)
            if aaaa_records is None:
                success = False
                continue

            for subdomain in subdomains:
                # Get current records
                if subdomain not in aaaa_records:
                    self.log.warning("Subdomain %s does not have AAAA records "
                                     "in zone %s.", subdomain, zone)
                    success = False
                    continue

                # Prefix == 128 is a special case
                if network.prefixlen == 128:
                    new_ip = network[0]
                    self.log.debug("Setting %s.%s AAAA record to prefix-128"
                                   "address %s", subdomain, zone, new_ip)
                    if not self.put_aaaa_records(zone, subdomain, [new_ip]):
                        success = False
                    continue

                # Update all the prefixes
                new_ips = []
                changed = False
                for aaaa in aaaa_records[subdomain]:
                    if aaaa in network:
                        if aaaa not in new_ips:
                            new_ips.append(aaaa)
                    else:
                        new_ip = self.replace_prefix(network, aaaa)
                        if new_ip not in new_ips:
                            new_ips.append(new_ip)
                        changed = True

                # Publish the updates
                if not changed:
                    self.log.info("Subdomain %s in zone %s already has "
                                  "addresses only in %s. Skipping.",
                                  subdomain, zone, network.compressed)
                else:
                    if not self.put_aaaa_records(zone, subdomain, new_ips):
                        success = False

        if not success:
            raise PublishError("Could not update all records")
