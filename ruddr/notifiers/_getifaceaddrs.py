"""Helper function for notifiers to look up IP addresses for the current
system's interfaces"""

# Netifaces is no longer currently maintained (looking for a new maintainer).
# But the last release was in 2021 and it's not that complex, especially the
# address lookup part, which hasn't been modified in several releases.
#
# If this gets to be a problem, a possible alternative is using ctypes or
# similar to call getifaddrs(3) directly, but that's basically what netifaces
# does already, in native C (and actually, it also has alternative
# implementations for Windows, AIX, and Solaris, which don't have getifaddrs).
#
# Some more information on this at:
# https://stackoverflow.com/questions/20743709/get-ipv6-addresses-in-linux-using-ioctl

import ipaddress
import netifaces
import sys


def _get_iface_addrs(if_name):
    """Lookup current addresses for the named interface.

    :param if_name: Name of the address to look up
    :return: A 2-tuple containing a list of IPV4Address followed by a list
             of IPV6Address.
    :raises ValueError: if there is not interface with the given name.
    """
    addresses = netifaces.ifaddresses(if_name)
    ipv4 = [a['addr'] for a in addresses[netifaces.AF_INET]]
    ipv6 = [a['addr'] for a in addresses[netifaces.AF_INET6]]

    # ipaddress.IPv6Address gets upset when there is %ifacename at the end
    # of an address in Python < 3.9. Chop it off.
    ipv6 = [a.partition('%')[0] for a in ipv6]

    ipv4 = [ipaddress.IPv4Address(a) for a in ipv4]
    ipv6 = [ipaddress.IPv6Address(a) for a in ipv6]

    return (ipv4, ipv6)


def get_iface_addrs(if_name, omit_private=True, omit_link_local=True):
    """Lookup current addresses for the named interface. Results will be
    ordered with non-private addresses first, then private (if requested), then
    link-local (if requested).

    :param if_name: Name of the address to look up
    :param omit_private: Whether to omit private addresses (including link- and
                         site-local)
    :param omit_link_local: Whether to omit link-local addresses
    :return: A 2-tuple containing a list of IPV4Address followed by a list
             of IPV6Address.
    :raises ValueError: if there is not interface with the given name.
    """
    ipv4, ipv6 = _get_iface_addrs(if_name)

    ipv4 = []
    ipv6 = []
    ipv4_private = []
    ipv6_private = []
    ipv4_link_local = []
    ipv6_link_local = []

    for a in ipv4:
        if a.is_link_local:
            ipv4_link_local.append(a)
        elif a.is_private:
            ipv4_private.append(a)
        else:
            ipv4.append(a)
    for a in ipv6:
        if a.is_link_local:
            ipv6_link_local.append(a)
        elif a.is_private:
            ipv6_private.append(a)
        else:
            ipv6.append(a)

    if not omit_private:
        ipv4 += ipv4_private
        ipv6 += ipv6_private
    if not omit_link_local:
        ipv4 += ipv4_link_local
        ipv6 += ipv6_link_local

    return (ipv4, ipv6)
