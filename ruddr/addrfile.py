"""Addrfile manager: Manages the addrfile for :class:`~ruddr.DDNSManager`"""

# Addrfile format:
#
# {
#     "updater_name": {
#         "ipv4": [ipv4, valid]
#         "ipv6": [ipv6, valid]
#     }
#     ...
# }
#
# where ipv4 and ipv6 are a strings with well-formed IPv4/IPv6 addresses or
# null (if there currently is no address of that type) and valid is a bool
# representing whether that address is current (true) or defunct (false)
#
# A missing address is treated the same as [null, false], and a missing
# updater is treated the same as if all its addresses were [null, false].

import ipaddress
import json
import logging
from typing import Optional, Tuple

log = logging.getLogger('ruddr')


class _IPJSONEncoder(json.JSONEncoder):
    """Subclass of JSONDecoder that can handle IPv4Address and IPv6Network"""
    def default(self, o):
        if isinstance(o, ipaddress.IPv4Address):
            return o.exploded
        elif isinstance(o, ipaddress.IPv6Network):
            return o.compressed
        return super().default(o)


def _extract_addr_tuple(entry, type_str, addr_constructor):
    if not isinstance(entry, list):
        log.warning(f"Malformed {type_str} entry in addrfile. Ignoring.")
        return (None, False)
    else:
        if len(entry) != 2:
            log.warning(f"Malformed {type_str} entry in addrfile. Ignoring.")
            return (None, False)
        try:
            entry[0] = addr_constructor(entry[0])
        except ValueError as e:
            log.warning(f"Malformed {type_str} in addrfile: {e}. Ignoring.")
            return (None, False)
        if not isinstance(entry[1], bool):
            log.warning(f"Malformed {type_str} entry in addrfile. Ignoring.")
            return (None, False)


def _decode_ips(d):
    """Object hook that decodes (ipaddr, is_current) pairs for "ipv4" and
    "ipv6" keys. If the pairs are malformed, logs the error and treats it as
    a non-current, unknown address (``(None, False)``).
    """
    if 'ipv4' in d:
        d['ipv4'] = _extract_addr_tuple(d['ipv4'],
                                        'IPv4',
                                        ipaddress.IPv4Address)
    if 'ipv6' in d:
        d['ipv6'] = _extract_addr_tuple(
            d['ipv6'],
            'IPv6',
            lambda x: ipaddress.IPv6Interface(x).network
        )
    return d


class Addrfile:
    """Manage an addrfile

    :param path: Path to the addrfile"""

    def __init__(self, path):
        #: Path to the addrfile
        self.path = path

        #: Address data. Stores the contents of the addrfile between writes.
        self.addresses: dict = self._read_addrfile()

    def _read_and_check_if_dict(self):
        """Read the addrfile in, confirm it is a dict, and return the dict"""
        try:
            with open(self.path, 'r') as f:
                addresses = json.load(f, object_hook=_decode_ips)
        except json.JSONDecodeError as e:
            log.warning("Malformed JSON in addrfile %s at (%d:%d). Will "
                        "recreate.", self.path, e.lineno, e.colno)
            return None
        except OSError as e:
            log.warning("Could not read addrfile %s (%s). Will attempt to "
                        "recreate.", self.path, e.strerror)
            return None

        if not isinstance(addresses, dict):
            log.warning("Addrfile %s has unexpected JSON structure. Will "
                        "recreate.", self.path)
            return None

        return addresses

    def _validate_updater_entries(self, addresses):
        """Validate that each updater's entry is a dict with the correct keys
        (values for each key are validated by object_hook during parsing)"""
        for name, addrs in list(addresses.items()):
            if not isinstance(addrs, dict):
                log.warning("Addrfile %s has unexpected JSON structure for "
                            "key %s. Will recreate that key.",
                            self.path, name)
                addresses[name] = {
                    'ipv4': (None, False),
                    'ipv6': (None, False),
                }
                continue

            for key in addrs:
                if key not in ('ipv4', 'ipv6'):
                    log.warning("Addrfile %s has unexpected JSON structure "
                                "for key %s. Will recreate that key.",
                                self.path, name)
                    addresses[name] = {
                        'ipv4': (None, False),
                        'ipv6': (None, False),
                    }
                    break
        return addresses

    def _read_addrfile(self):
        """Read the addrfile in. If it cannot be read or is malformed, log and
        return without touching :attr:`self.addresses`."""
        addresses = self._read_and_check_if_dict()
        if addresses is not None:
            return self._validate_updater_entries(addresses)
        else:
            return dict()

    def _write_addrfile(self):
        """Write out the addrfile. If it cannot be written, log the error but
        do not raise an exception."""
        try:
            with open(self.path, 'w') as f:
                json.dump(self.addresses, f, cls=_IPJSONEncoder,
                          sort_keys=True, indent=4)
        except OSError as e:
            log.error("Could not write addrfile %s: %s",
                      self.path, e.strerror)

    def get_ipv4(self,
                 name: str) -> Tuple[Optional[ipaddress.IPv4Address], bool]:
        """Get the IPv4 entry from the addrfile for the named updater.

        If the file could not be opened, there was no entry for the named
        updater, or the addrfile or entry were malformed, returns
        ``(None, False)``.

        :param name: Name of the updater to fetch the address for
        :return: A tuple ``(address, is_current)``. ``address`` is an
                 :class:`~ipaddress.IPv4Address`, or ``None`` if there
                 currently is no IPv4 address. ``is_current`` is a
                 :class:`bool` representing whether the current address is
                 known to be published. Note that ``(None, True)`` *is* a valid
                 response, and represents an intentional, known lack of IP
                 address (e.g. if a host has *only* an IPv6 address and its
                 IPv4 address is intentionally de-published).
        """
        try:
            addrs = self.addresses[name]
        except KeyError:
            return (None, False)

        try:
            return addrs['ipv4']
        except KeyError:
            return (None, False)

    def get_ipv6(self,
                 name: str) -> Tuple[Optional[ipaddress.IPv6Network], bool]:
        """Get the IPv6 entry from the addrfile for the named updater.

        If the file could not be opened, there was no entry for the named
        updater, or the addrfile or entry were malformed, returns
        ``(None, False)``.

        :param name: Name of the updater to fetch the address for
        :return: A tuple ``(prefix, is_current)``. ``prefix`` is an
                 :class:`~ipaddress.IPv6Network`, or ``None`` if there
                 currently is no IPv6 prefix. ``is_current`` is a
                 :class:`bool` representing whether the current prefix is
                 known to be published. Note that ``(None, True)`` *is* a valid
                 response, and represents an intentional, known lack of IP
                 address (e.g. if a host has *only* an IPv4 address and its
                 IPv6 prefix is intentionally de-published).
        """
        try:
            addrs = self.addresses[name]
        except KeyError:
            return (None, False)

        try:
            return addrs['ipv6']
        except KeyError:
            return (None, False)

    def set_ipv4(self, name: str, address: Optional[ipaddress.IPv4Address]):
        """Write the given updater's IPv4 address to the addrfile

        :param name: The name of the updater
        :param address: The IPv4 address to write, or None if the IPv4 address
                        was unpublished
        """
        if name in self.addresses:
            self.addresses[name]['ipv4'] = (address, True)
        else:
            self.addresses[name] = {'ipv4': (address, True)}
        self._write_addrfile()

    def set_ipv6(self, name: str, prefix: Optional[ipaddress.IPv6Network]):
        """Write the given updater's IPv6 prefix to the addrfile

        :param name: The name of the updater
        :param prefix: The IPv6 prefix to write, or None if the IPv6 prefix was
                       unpublished
        """
        if name in self.addresses:
            self.addresses[name]['ipv6'] = (prefix, True)
        else:
            self.addresses[name] = {'ipv6': (prefix, True)}
        self._write_addrfile()

    def invalidate_ipv4(self,
                        name: str,
                        address: Optional[ipaddress.IPv4Address]):
        """Set the given updater's IPv4 address to defunct

        :param name: The name of the updater
        :param address: The desired IPv4 address that failed to publish
        """
        if name in self.addresses:
            self.addresses[name]['ipv4'] = (address, False)
        else:
            self.addresses[name] = {'ipv4': (address, False)}
        self._write_addrfile()

    def invalidate_ipv6(self,
                        name: str,
                        prefix: Optional[ipaddress.IPv6Network]):
        """Set the given updater's IPv6 prefix to defunct

        :param name: The name of the updater
        :param prefix: The desired IPv6 prefix that failed to publish
        """
        if name in self.addresses:
            self.addresses[name]['ipv6'] = (prefix, False)
        else:
            self.addresses[name] = {'ipv6': (prefix, False)}
        self._write_addrfile()

    def needs_ipv4_update(self,
                          name: str,
                          address: Optional[ipaddress.IPv4Address]):
        """Return True or False indicating whether the given IPv4 address
        requires publishing an update for the given updater

        :param name: The name of the updater
        :param address: The desired IPv4 address, or None if there should be no
                        IPv4 address
        """
        current_addr, is_current = self.get_ipv4(name)
        if not is_current:
            return True
        if current_addr != address:
            return True

    def needs_ipv6_update(self,
                          name: str,
                          prefix: Optional[ipaddress.IPv6Network]):
        """Return True or False indicating whether the given IPv6 prefix
        requires publishing an update for the given updater

        :param name: The name of the updater
        :param prefix: The desired IPv6 prefix, or None if there should be no
                        IPv6 prefix
        """
        current_prefix, is_current = self.get_ipv6(name)
        if not is_current:
            return True
        if current_prefix != prefix:
            return True
