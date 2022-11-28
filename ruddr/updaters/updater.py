"""Base class for Ruddr updaters"""

import functools
import ipaddress
import logging
import socket
import threading
import types
from typing import Union, Tuple, List, Optional

import dns.resolver

from ..exceptions import PublishError, FatalPublishError, ConfigError


class Retry:
    """A decorator that makes a function retry periodically until success.
    Success is defined by not raising :exc:`~ruddr.PublishError`. The first
    retry interval is 5 minutes, with exponential backoff until the retry
    interval reaches 1 day, at which point it will remain constant.

    Additional calls to the function while a retry is pending are ignored if
    the parameters are equal. Otherwise, the previously pending retry is
    cancelled, the call is executed, and the retry timer resets as if it were a
    fresh failure.

    Assumes it is being applied to a method of a :class:`BaseUpdater`. Other
    uses may not work as intended."""

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.retrying = False
        self.last_args = None
        self.last_kwargs = None
        self.seq = 0
        self.retries = 0
        self.lock = threading.RLock()

    # Emulate binding behavior in normal functions that become methods.
    # See https://docs.python.org/3/howto/descriptor.html#functions-and-methods
    # (Without this, the 'self' argument is not passed through)
    def __get__(self, obj, obj_cls=None):
        if obj is None:
            # This check is not strictly necessary in this case...it only
            # evaluates to True when calling a decorated method that's not
            # @staticmethod and not @classmethod using the class name
            # (e.g. Class.my_func()). We don't do that.
            return self
        return types.MethodType(self, obj)

    def __call__(self, obj, *args, **kwargs):
        with self.lock:
            if (self.retrying and
                    self.last_args == args and self.last_kwargs == kwargs):
                obj.log.debug("(Not executing call with equal args to seq %d)",
                              self.seq)
                return
            self.seq += 1
            self.retries = 0
            obj.log.debug("(Update seq: %d)", self.seq)
            self.wrapper(self.seq, obj, *args, **kwargs)

    def retry(self, seq, obj, *args, **kwargs):
        """Retry the function. Verifies that no attempt has been made in the
        meantime."""
        with self.lock:
            if self.seq != seq:
                # Another update has happened in the time since this retry was
                # scheduled. Abort.
                obj.log.debug("(Retry for update seq %d aborted due to new "
                              "update in the meantime.", seq)
            else:
                obj.log.debug("(Retry for update seq: %d)", seq)
                self.wrapper(seq, obj, *args, **kwargs)

    def wrapper(self, seq, obj, *args, **kwargs):
        """Run the function and schedule a retry if it failed"""
        try:
            self.func(obj, *args, **kwargs)
        except FatalPublishError:
            self.retrying = False
            obj.log.error("Update error was fatal. This updater will halt.")
            obj.halt = True
        except PublishError:
            self.retrying = True
            # Retry after minimum interval the first time, doubling each retry
            retry_delay = obj.min_retry_interval * (2 ** self.retries)
            if retry_delay > 86400:
                # Cap retry time at one day
                retry_delay = 86400
            self.retries += 1
            obj.log.info("Update failed. Retrying in %d minutes.",
                         retry_delay // 60)
            timer = threading.Timer(retry_delay, self.retry,
                                    args=(seq, obj, *args), kwargs=kwargs)
            timer.daemon = True
            timer.start()
        else:
            self.retrying = False


class BaseUpdater:
    """Skeletal superclass for :class:`Updater`. Custom updaters can opt to
    override this instead if the default logic in Updater does not suit their
    needs (e.g. if the protocol requires IPv4 and IPv6 updates to be sent
    simultaneously, custom retry logic, etc.).

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param min_retry: The minimum number of seconds between retries, if a retry
                      is necessary. (An exponential backoff is applied after
                      the first retry.)
    """

    def __init__(self, name, addrfile, min_retry=300):
        #: Updater name (from config section heading)
        self.name = name

        #: Logger (see standard :mod:`logging` module)
        # NOTE: This name is also used by @Retry
        self.log = logging.getLogger(f'ruddr.updater.{self.name}')

        #: Addrfile for avoiding duplicate updates
        self.addrfile = addrfile

        #: Minimum retry interval (some providers may require a minimum delay
        #: when there are server errors)
        self.min_retry_interval = min_retry

        #: @Retry will set this to ``True`` when there has been a fatal error
        #: and no more updates should be issued.
        self.halt = False

    def initial_update(self):
        """Do the initial update: Check the addrfile, and if either address is
        defunct but has a last-attempted-address, try to publish it again.
        """
        raise NotImplementedError

    def update_ipv4(self, address):
        """Receive a new IPv4 address from the attached notifier. If it does
        not match the current address, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv4Address` to update with
        """
        raise NotImplementedError

    def update_ipv6(self, address):
        """Receive a new IPv6 prefix from the attached notifier. If it does
        not match the current prefix, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv6Network` to update with
        """
        raise NotImplementedError

    @staticmethod
    def replace_ipv6_prefix(
            network: ipaddress.IPv6Network,
            address: ipaddress.IPv6Address
    ) -> ipaddress.IPv6Address:
        """Replace the prefix portion of the given IPv6 address with the network
        prefix provided and return the result"""
        host = int(address) & ((1 << (128 - network.prefixlen)) - 1)
        return network[host]


class Updater(BaseUpdater):
    """Base class for Ruddr updaters. Handles setting up logging, attaching to
    a notifier, retries, and working with the addrfile.

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    """

    def initial_update(self):
        """Do the initial update: Check the addrfile, and if either address is
        defunct but has a last-attempted-address, try to publish it again.
        """
        ipv4, is_current = self.addrfile.get_ipv4(self.name)
        if not is_current:
            self.update_ipv4(ipv4)

        ipv6, is_current = self.addrfile.get_ipv6(self.name)
        if not is_current:
            self.update_ipv6(ipv6)

    @Retry
    def update_ipv4(self, address):
        """Receive a new IPv4 address from the attached notifier. If it does
        not match the current address, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv4Address` to update with
        """
        if self.halt:
            return

        if address is None:
            self.log.info("Skipping update with no address (will not "
                          "de-publish)")
        if not self.addrfile.needs_ipv4_update(self.name, address):
            self.log.debug("Skipping update as %s is current address",
                           address.exploded)
            return

        # Invalidate current address before publishing. If publishing fails,
        # current address is indeterminate.
        self.addrfile.invalidate_ipv4(self.name, address)

        try:
            self.publish_ipv4(address)
        except PublishError:
            self.log.error("Failed to publish address %s", address)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv4 updates")
            return

        self.addrfile.set_ipv4(self.name, address)

    @Retry
    def update_ipv6(self, prefix):
        """Receive a new IPv6 prefix from the attached notifier. If it does
        not match the current prefix, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param prefix: :class:`IPv6Network` to update with
        """
        if self.halt:
            return

        if prefix is None:
            self.log.info("Skipping update with no prefix (will not "
                          "de-publish)")
        if not self.addrfile.needs_ipv6_update(self.name, prefix):
            self.log.debug("Skipping update as %s is current address",
                           prefix.compressed)
            return

        # Invalidate current prefix before publishing. If publishing fails,
        # current prefix is indeterminate.
        self.addrfile.invalidate_ipv6(self.name, prefix)

        try:
            self.publish_ipv6(prefix)
        except PublishError:
            self.log.error("Failed to publish prefix %s", prefix)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv6 updates")
            return

        self.addrfile.set_ipv6(self.name, prefix)

    def publish_ipv4(self, address: ipaddress.IPv4Address):
        """Publish a new IPv4 address to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        Must be implemented by subclasses if they support IPv4 updates. Be sure
        to raise :exc:`~ruddr.PublishError` when publishing fails!

        :param address: :class:`IPv4Address` to publish
        :raise PublishError: when publishing fails
        """
        raise NotImplementedError("IPv4 publish function not provided")

    def publish_ipv6(self, network: ipaddress.IPv6Network):
        """Publish a new IPv6 prefix to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        Must be implemented by subclasses if they support IPv6 updates. Be sure
        to raise :exc:`~ruddr.PublishError` when publishing fails!

        :param network: :class:`IPv6Network` with the prefix to publish
        :raise PublishError: when publishing fails
        """
        raise NotImplementedError("IPv6 publish function not provided")


class OneWayUpdater(Updater):
    """Base class for updaters supporting protocols that are one-way, that is,
    the API has no way to obtain the current address for a host. It can use
    hardcoded IPv6 addresses or look them up in DNS.

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param hosts: A list of tuples (hostname, None|IPv6Address|fqdn)
                  specifying where each host portion of IPv6 addresses should
                  come from
    :param nameserver: The nameserver to use to look up AAAA records for the
                       FQDNs, if any. If ``None``, system DNS is used.
    """

    def __init__(
        self,
        name,
        addrfile,
        hosts,
        nameserver: Optional[str] = None,
        min_retry=300
    ):
        super().__init__(name, addrfile, min_retry)

        #: A list of hosts and how to get the host portion of their IPv6s
        self.hosts = hosts
        if isinstance(self.hosts, str):
            self.hosts = self.split_hosts(self.hosts)

        #: Nameserver to use when looking up AAAA records for FQDNs in hosts
        self.nameserver = nameserver

    def split_hosts(
            self,
            hosts: str
    ) -> List[Tuple[str, Optional[Union[ipaddress.IPv6Address, str]]]]:
        """Helper function to split a hosts string into a list of (hostname,
        None|IPv6Address|hostname).

        Given a whitespace-separated list of entries in the following formats:

        - ``foo/-``
        - ``foo/foo.example.com``
        - ``foo/::1a2b:3c3d``

        produce a list of tuples where the first entry is the hostname to
        update and the second entry is an :class:`~ipaddress.IPv6Address`,
        :class:`str` FQDN, or ``None`` indicating how to get the host portion
        of the IPv6 address.

        :param hosts: The whitespace-separated list
        :returns: The list of host tuples
        """
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
            except ValueError:
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
                self.publish_ipv4_one_host(host, address)
            except PublishError as e:
                if error is None:
                    error = e
        if error is not None:
            raise error

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
        raise NotImplementedError

    def publish_ipv6(self, network):
        error = None
        for host, ip_lookup in self.hosts:
            if ip_lookup is None:
                continue
            try:
                current_ip = self._get_current_ipv6(host, ip_lookup)
                new_ipv6 = self.replace_ipv6_prefix(network, current_ip)
                self.publish_ipv6_one_host(host, new_ipv6)
            except PublishError as e:
                if error is None:
                    error = e
        if error is not None:
            raise error

    def _get_current_ipv6(
        self,
        hostname: str,
        ip_lookup: Union[str, ipaddress.IPv6Address]
    ) -> ipaddress.IPv6Address:
        """Get the current IPv6 address for a host, either returning the
        hardcoded value or doing a DNS lookup. Convert errors to
        :class:`PublishError`.

        :param hostname: The host to fetch the IPv6 for
        :param ip_lookup: A hardcoded :class:`~ipaddress.IPv6Address` or an
                          FQDN to fetch an AAAA record from

        :raises PublishError: if fetching the IPv6 failed
        :returns: An :class:`~ipaddress.IPv6Address` with the current IPv6
        """
        if isinstance(ip_lookup, ipaddress.IPv6Address):
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
        return current_ipv6

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
        raise NotImplementedError
