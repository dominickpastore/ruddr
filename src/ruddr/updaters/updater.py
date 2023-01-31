"""Base class for Ruddr updaters"""

import functools
import ipaddress
import logging
import socket
import threading
import types
# Note: We are not using abstractmethod the way it is intended. We are using it
# purely to get Sphinx to mark methods as abstract. Thus, we intentionally do
# NOT use ABCMeta or inherit from ABC.
from abc import abstractmethod
from typing import (Union, Tuple, List, Optional, Dict, TypeVar, Sequence,
                    Mapping, Callable)

import dns.exception    # type: ignore
import dns.resolver     # type: ignore

from ruddr.addrfile import Addrfile
from ruddr.exceptions import PublishError, FatalPublishError, ConfigError
from ruddr.util import ZoneSplitter


Addr = TypeVar('Addr', ipaddress.IPv4Address, ipaddress.IPv6Address)


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
        self.func: Callable = func
        self.retrying: bool = False
        self.last_args: Optional[Sequence] = None
        self.last_kwargs: Optional[Mapping] = None
        self.seq: int = 0
        self.retries: int = 0
        self.lock: threading.RLock = threading.RLock()

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

    # TODO #32: from __future__ import anotations means this doesn't have to be
    #  a string
    def __call__(self, obj: 'BaseUpdater', *args, **kwargs):
        with self.lock:
            if (self.retrying and
                    self.last_args == args and self.last_kwargs == kwargs):
                obj.log.debug("(Not executing call with equal args to seq %d)",
                              self.seq)
                return
            self.seq += 1
            self.retries = 0
            self.last_args = args
            self.last_kwargs = kwargs
            obj.log.debug("(Update seq: %d)", self.seq)
            self.wrapper(self.seq, obj, *args, **kwargs)

    def retry(self, seq: int, obj: 'BaseUpdater', *args, **kwargs):
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

    def wrapper(self, seq: int, obj: 'BaseUpdater', *args, **kwargs):
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
    """Skeletal superclass for :class:`Updater`. It sets up the logger, sets up
    some useful member variables, and little else. Custom updaters can opt to
    override this instead if the default logic in Updater does not suit their
    needs (e.g. if the protocol requires IPv4 and IPv6 updates to be sent
    simultaneously, custom retry logic, etc.).

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    """

    def __init__(self, name: str, addrfile: Addrfile):
        #: Updater name (from config section heading)
        self.name: str = name

        #: Logger (see standard :mod:`logging` module)
        # NOTE: This name is also used by @Retry
        self.log: logging.Logger = logging.getLogger(
            f'ruddr.updater.{self.name}'
        )

        #: Addrfile for avoiding duplicate updates
        self.addrfile: Addrfile = addrfile

        #: Minimum retry interval (some providers may require a minimum delay
        #: when there are server errors, in which case, subclasses can modify
        #: this)
        self.min_retry_interval: int = 300

        #: ``@Retry`` will set this to ``True`` when there has been a fatal
        #: error and no more updates should be issued.
        self.halt: bool = False

    def initial_update(self):
        """Do the initial update: Check the addrfile, and if either address is
        defunct but has a last-attempted-address, try to publish it again.
        """
        raise NotImplementedError

    def update_ipv4(self, address: ipaddress.IPv4Address):
        """Receive a new IPv4 address from the attached notifier. If it does
        not match the current address, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv4Address` to update with
        """
        raise NotImplementedError

    def update_ipv6(self, address: ipaddress.IPv6Network):
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
        """Replace the prefix portion of the given IPv6 address with the
        network prefix provided and return the result

        :param network: The network prefix to set
        :param address: The address to set the network prefix on

        :return: The modified address
        """
        host = int(address) & ((1 << (128 - network.prefixlen)) - 1)
        return network[host]


class Updater(BaseUpdater):
    """Base class for Ruddr updaters. Handles setting up logging, retries, the
    initial update, and working with the addrfile.

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    """

    def __init__(self, name: str, addrfile: Addrfile):
        super().__init__(name, addrfile)

    def initial_update(self):
        """:meta private:"""
        self.log.debug("Doing initial update")
        ipv4, is_current = self.addrfile.get_ipv4(self.name)
        if not is_current:
            self.log.info("IPv4 not known to be current, doing initial update")
            self.update_ipv4(ipv4)

        ipv6, is_current = self.addrfile.get_ipv6(self.name)
        if not is_current:
            self.log.info("IPv6 not known to be current, doing initial update")
            self.update_ipv6(ipv6)

    @Retry
    def update_ipv4(self, address: ipaddress.IPv4Address):
        """:meta private:"""
        if self.halt:
            return

        # TODO This won't behave well and shouldn't be allowed. If an address
        #  can't currently be found the notifier should just not notify.
        # TODO Also update Addrfile.set_ipv4 not to accept None.
        if address is None:
            self.log.info("Skipping update with no address (will not try to "
                          "de-publish)")
            return
        if not self.addrfile.needs_ipv4_update(self.name, address):
            self.log.debug("Skipping update as %s is current address",
                           address.exploded)
            return

        # Invalidate current address before publishing. If publishing fails,
        # current address is indeterminate.
        try:
            self.addrfile.invalidate_ipv4(self.name, address)
        except OSError as e:
            self.log.critical("Could not invalidate IPv4 in addrfile: %s", e)
            raise FatalPublishError(f"Updater {self.name} could not invalidate"
                                    "IPv4 in addrfile") from e

        try:
            self.publish_ipv4(address)
        except PublishError:
            self.log.error("Failed to publish address %s", address)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv4 updates")
            return

        try:
            self.addrfile.set_ipv4(self.name, address)
        except OSError as e:
            self.log.critical("New IPv4 could not be written to addrfile: "
                              "%s", e)
            raise FatalPublishError(f"Updater {self.name} could not write "
                                    "IPv4 to addrfile") from e

    @Retry
    def update_ipv6(self, prefix: ipaddress.IPv6Network):
        """:meta private:"""
        if self.halt:
            return

        # TODO This won't behave well and shouldn't be allowed. If an address
        #  can't currently be found the notifier should just not notify.
        # TODO Also update Addrfile.set_ipv6 not to accept None.
        if prefix is None:
            self.log.info("Skipping update with no prefix (will not try to "
                          "de-publish)")
            return
        if not self.addrfile.needs_ipv6_update(self.name, prefix):
            self.log.debug("Skipping update as %s is current address",
                           prefix.compressed)
            return

        # Invalidate current prefix before publishing. If publishing fails,
        # current prefix is indeterminate.
        try:
            self.addrfile.invalidate_ipv6(self.name, prefix)
        except OSError as e:
            self.log.critical("Could not invalidate IPv6 in addrfile: %s", e)
            raise FatalPublishError(f"Updater {self.name} could not invalidate"
                                    "IPv6 in addrfile") from e

        try:
            self.publish_ipv6(prefix)
        except PublishError:
            self.log.error("Failed to publish prefix %s", prefix)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv6 updates")
            return

        try:
            self.addrfile.set_ipv6(self.name, prefix)
        except OSError as e:
            self.log.critical("New IPv6 could not be written to addrfile: "
                              "%s", e)
            raise FatalPublishError(f"Updater {self.name} could not write "
                                    "IPv6 to addrfile") from e

    def publish_ipv4(self, address: ipaddress.IPv4Address):
        """Publish a new IPv4 address to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        **Must be implemented by subclasses if they support IPv4 updates.**

        :param address: :class:`IPv4Address` to publish
        :raise PublishError: when publishing fails (will retry automatically
                             after a delay)
        """
        raise NotImplementedError("IPv4 publish function not provided")

    def publish_ipv6(self, network: ipaddress.IPv6Network):
        """Publish a new IPv6 prefix to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        **Must be implemented by subclasses if they support IPv6 updates.**

        :param network: :class:`IPv6Network` with the prefix to publish
        :raise PublishError: when publishing fails (will retry automatically
                             after a delay)
        """
        raise NotImplementedError("IPv6 publish function not provided")


class TwoWayZoneUpdater(Updater):
    """Base class for updaters supporting protocols that are two-way and
    zone-based, that is:

    - The API supports fetching the current address(es) for hosts, either
      individually or by fetching whole zones
    - The API involves zones in some way, e.g. entire zones can be fetched or
      updated at once, or fetching/updating a single domain requires specifying
      its zone

    It's meant to be flexible enough for a variety of API styles. For example,
    some APIs may be very flexible, allowing individual domains' records to be
    fetched and updated. Others may be strictly zone-based, only providing APIs
    to fetch and replace entire zones. Still others may be a hybrid, with a
    way to fetch an entire zone but only update single domains. This class
    supports all of the above by allowing only the appropriate methods to be
    implemented.

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param datadir: The configured data directory
    """

    def __init__(self, name: str, addrfile: Addrfile, datadir: str):
        super().__init__(name, addrfile)

        #: List of hosts to keep updated, as FQDNs, along with any
        #: explicitly-specified zones they reside in
        self._hosts: List[Tuple[str, Optional[str]]] = []

        #: Used by :func:`_get_subdomain_and_zone_for`
        self._zone_splitter: Optional[ZoneSplitter] = None
        self._datadir: str = datadir

    def init_hosts_and_zones(
        self,
        hosts: Union[List[Tuple[str, Optional[str]]], str]
    ):
        """Provide the list of hosts to be updated, optionally with their zones
        if configured.

        This is separate from :meth:`__init__` so subclasses can rely on the
        logger while doing their config parsing, then pass the list of hosts
        in via this method after. **It must be called before your subclass's
        constructor completes.**

        The list can be provided either as an unparsed :class:`str` or as a
        list of 2-tuples ``(fqdn, zone)``:

        - When provided as an unparsed :class:`str`, it should be a
          whitespace-separated list whose items are in the format
          ``foo.example.com`` or ``foo.example.com/example.com`` (the latter
          format explicitly setting the zone)

        - When provided as a list of 2-tuples, ``fqdn`` is the FQDN for the
          host and ``zone`` is either ``None`` or a :class:`str` explicitly
          specifying the zone for this host.

        For hosts without a zone explicitly specified (which can be all of
        them), Ruddr will use :meth:`get_zones` to determine the zone, or the
        `public suffix list`_ if :meth:`get_zones` is not implemented.

        .. _public suffix list: https://publicsuffix.org/

        :param hosts: The list of hosts to be updated

        :raises ConfigError: if an FQDN does not reside in the zone provided
                             with it, or is a duplicate
        """
        if isinstance(hosts, str):
            self._hosts = []
            for host in hosts.split():
                fqdn, sep, zone = host.partition('/')
                if sep == '':
                    zone = None
                self._check_zone_and_duplicates(fqdn, zone)
                self._hosts.append((fqdn, zone))
        else:
            for fqdn, zone in hosts:
                self._check_zone_and_duplicates(fqdn, zone)
            self._hosts = hosts

    def _check_zone_and_duplicates(self, fqdn: str, zone: str):
        """Check if the given FQDN is in the given zone and that it is not a
        duplicate of any existing hosts

        :param fqdn: The FQDN to check
        :param zone: The zone to check
        :raise ConfigError: if the FQDN is not in the given zone or is a
                            duplicate
        """
        if zone is not None:
            try:
                self.subdomain_of(fqdn, zone)
            except ValueError:
                self.log.critical("Domain '%s' is not in zone '%s'",
                                  fqdn, zone)
                raise ConfigError(f"Domain {fqdn} in updater {self.name} "
                                  f"is not in zone {zone}") from None
        for host, _ in self._hosts:
            if fqdn == host:
                self.log.critical("Domain '%s' is listed multiple times", fqdn)
                raise ConfigError(f"Updater {self.name} has domain {fqdn} "
                                  "listed multiple times")

    @abstractmethod
    def get_zones(self) -> List[str]:
        """Get a list of zones under the account.

        **Implementing this method in subclasses is optional.**

        If implemented, this function should return a list of zones (more
        specifically, the domain name for each zone). The FQDNs-to-be-updated
        will be compared against the zone list. This serves two purposes:

        1. It allows better error checking. If any of the FQDNs do not fall
           into one of the available zones, Ruddr can catch that and log it for
           the user.

        2. If any of the zones are not immediate subdomains of a public suffix
           (public suffix being .com, .co.uk, etc., see `public suffix list`_),
           for example, myzone.provider.com, this allows Ruddr to get the
           correct zone without it being manually configured.

        If not implemented, Ruddr uses the `public suffix list`_ to assign
        zones to any FQDNs without explicitly-configured zones.

        .. _public suffix list: https://publicsuffix.org/

        :return: A list of zones

        :raises NotImplementedError: if not implemented
        :raises PublishError: if fetching the zones is implemented, but failed
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_zone_ipv4s(
        self,
        zone: str
    ) -> List[Tuple[str, ipaddress.IPv4Address, Optional[int]]]:
        """Get a list of A (IPv4) records for the given zone.

        **Implementing this method in subclasses is optional.** If not
        implemented, then :meth:`fetch_subdomain_ipv4s` and
        :meth:`put_subdomain_ipv4` must be implemented.

        If implemented, this function should return a list of A (IPv4) records
        in the given zone in the form ``(name, addr, ttl)`` where ``name`` is
        the subdomain portion (e.g. a record for "foo.bar.example.com" in zone
        "example.com" should return "foo.bar" as the name), ``addr`` is an
        :class:`~ipaddress.IPv4Address`, and ``ttl`` is the TTL of the record.

        Some notes:

        - ``name`` should be empty for the root domain in the zone

        - The :meth:`subdomain_of` function may be helpful for the ``name``
          element if the provider's API returns FQDNs

        - The ``ttl`` may be set to ``None`` if the API does not provide it. It
          is only required for providers that would change the TTL back to
          default if it's not explicitly included when Ruddr later updates the
          record.

        - If there are multiple records/IPv4s for a single subdomain, return
          them as separate list items with the same ``name``. Note that if the
          subdomain needs to be updated by Ruddr, it will only produce a single
          record to replace them.

        :param zone: The zone to fetch records for

        :return: A list of A records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or the
                              zone does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_zone_ipv6s(
            self,
            zone: str
    ) -> List[Tuple[str, ipaddress.IPv6Address, Optional[int]]]:
        """Get a list of AAAA (IPv6) records for the given zone.

        **Implementing this method in subclasses is optional.** If not
        implemented, then :meth:`fetch_subdomain_ipv6s` and
        :meth:`put_subdomain_ipv6s` must be implemented.

        If implemented, this function should return a list of AAAA (IPv6)
        records in the given zone in the form ``(name, addr, ttl)`` where
        ``name`` is the subdomain portion (e.g. a record for
        "foo.bar.example.com" in zone "example.com" should return "foo.bar" as
        the name), ``addr`` is an :class:`~ipaddress.IPv6Address`, and ``ttl``
        is the TTL of the record.

        Some notes:

        - ``name`` should be empty for the root domain in the zone

        - The :meth:`subdomain_of` function may be helpful for the ``name``
          element if the provider's API returns FQDNs

        - The ``ttl`` may be set to ``None`` if the API does not provide it. It
          is only required for providers that would change the TTL back to
          default if it's not explicitly included when Ruddr later updates the
          record.

        - If there are multiple records/IPv6s for a single subdomain, return
          them as separate list items with the same ``name``. If the subdomain
          needs to be updated by Ruddr, it will update all of them.

        :param zone: The zone to fetch records for

        :return: A list of AAAA records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or the
                              zone does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_subdomain_ipv4s(
        self,
        subdomain: str,
        zone: str,
    ) -> List[Tuple[ipaddress.IPv4Address, Optional[int]]]:
        """Get a list of A (IPv4) records for the given domain.

        **Implementing this method in subclasses is optional.** It only needs
        to be implemented if :meth:`fetch_zone_ipv4s` is not implemented.

        This function should return a list of A (IPv4) records for the given
        domain. If this provider's API requires using the original FQDN (rather
        than separate subdomain and zone fields), use :meth:`fqdn_of` on the
        parameters to obtain it.

        The return value is a list of tuples ``(addr, ttl)`` where ``addr`` is
        an :class:`~ipaddress.IPv4Address` and ``ttl`` is the TTL of the
        record. As with :meth:`fetch_zone_ipv4s`:

        - The ``ttl`` may be set to ``None`` if the API does not provide it. It
          is only required for providers that would change the TTL back to
          default if it's not explicitly included when Ruddr later updates the
          record.

        - The return value is a list in case there is more than one A record
          associated with the domain; however, note that Ruddr will want to
          replace all of them with a single record.

        :param subdomain: The subdomain to fetch records for (only the
                          subdomain portion), empty for the root domain of the
                          zone
        :param zone: The zone the subdomain belongs to

        :return: A list of A records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or no
                              such record exists
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_subdomain_ipv6s(
            self,
            subdomain: str,
            zone: str
    ) -> List[Tuple[ipaddress.IPv6Address, Optional[int]]]:
        """Get a list of AAAA (IPv6) records for the given domain.

        **Implementing this method in subclasses is optional.** It only needs
        to be implemented if :meth:`fetch_zone_ipv6s` is *not* implemented.

        This function should return a list of AAAA (IPv6) records for the given
        domain. If this provider's API requires using the original FQDN (rather
        than separate subdomain and zone fields), use :meth:`fqdn_of` on the
        parameters to obtain it.

        The return value is a list of tuples ``(addr, ttl)`` where ``addr`` is
        an :class:`~ipaddress.IPv6Address` and ``ttl`` is the TTL of the
        record. As with :meth:`fetch_zone_ipv6s`:

        - The ``ttl`` may be set to ``None`` if the API does not provide it. It
          is only required for providers that would change the TTL back to
          default if it's not explicitly included when Ruddr later updates the
          record.

        - The return value is a list in case there is more than one AAAA record
          associated with the domain. Ruddr will update all of them.

        :param subdomain: The subdomain to fetch records for (only the
                          subdomain portion), empty for the root domain of the
                          zone
        :param zone: The zone the subdomain belongs to

        :return: A list of AAAA records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or no
                              such record exists
        """
        raise NotImplementedError

    @abstractmethod
    def put_zone_ipv4s(
        self,
        zone: str,
        records: Dict[str, Tuple[List[ipaddress.IPv4Address], Optional[int]]],
    ):
        """Publish A (IPv4) records for the given zone.

        **Implementing this method in subclasses is optional.** However, either
        this function or :meth:`put_subdomain_ipv4` must be implemented. The
        latter must be implemented if :meth:`fetch_zone_ipv4s` is not
        implemented.

        If implemented, this function should replace all the A records for the
        given zone with the records provided. The records are provided as a
        :class:`dict` where the keys are the subdomain names and the values are
        2-tuples ``(addrs, ttl)`` where ``addrs`` is a list of
        :class:`~ipaddress.IPv4Address` and ``ttl`` is an :class:`int` (or
        ``None`` if the :meth:`fetch_zone_ipv4s` function didn't provide any).

        Records that Ruddr is not configured to update will be passed through
        from :meth:`fetch_zone_ipv4s` unmodified.

        :param zone: The zone to publish records for
        :param records: The records to publish

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    @abstractmethod
    def put_zone_ipv6s(
        self,
        zone: str,
        records: Dict[str, Tuple[List[ipaddress.IPv6Address], Optional[int]]]
    ):
        """Publish AAAA (IPv6) records for the given zone.

        **Implementing this method in subclasses is optional.** However, either
        this function or :meth:`put_subdomain_ipv6s` must be implemented. The
        latter must be implemented if :meth:`fetch_zone_ipv6s` is not
        implemented.

        If implemented, this function should replace all the AAAA records for
        the given zone with the records provided. The records are provided as a
        :class:`dict` where the keys are the subdomain names and the values are
        2-tuples ``(addrs, ttl)`` where ``addrs`` is a list of
        :class:`~ipaddress.IPv6Address` and ``ttl`` is an :class:`int` (or
        ``None`` if the :meth:`fetch_zone_ipv6s` function didn't provide any).

        Records that Ruddr is not configured to update will be passed through
        from :meth:`fetch_zone_ipv6s` unmodified.

        :param zone: The zone to publish records for
        :param records: The records to publish

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    @abstractmethod
    def put_subdomain_ipv4(self, subdomain: str, zone: str,
                           address: ipaddress.IPv4Address, ttl: Optional[int]):
        """Publish an A (IPv4) record for the given domain.

        **Implementing this method in subclasses is optional.** However, it
        must be implemented if either :meth:`fetch_zone_ipv4s` or
        :meth:`put_zone_ipv4s` are not implemented.

        This function should replace the A records for the given domain with a
        single A record matching the given parameters. If this provider's API
        requires using the original FQDN (rather than separate subdomain and
        zone fields), use :meth:`fqdn_of` on the parameters to obtain it.

        This will only be called for the domains Ruddr is configured to update.

        :param subdomain: The subdomain to publish the record for (only the
                          subdomain portion), empty for the root domain of the
                          zone
        :param zone: The zone the subdomain belongs to
        :param address: The address for the new record
        :param ttl: The TTL for the new record (or ``None`` if the
                    ``fetch_*_ipv4s`` functions didn't provide any). Ruddr
                    passes this through unchanged.

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    @abstractmethod
    def put_subdomain_ipv6s(self, subdomain: str, zone: str,
                            addresses: List[ipaddress.IPv6Address],
                            ttl: Optional[int]):
        """Publish AAAA (IPv6) records for the given domain.

        **Implementing this method in subclasses is optional.** However, it
        must be implemented if either :meth:`fetch_zone_ipv6s` or
        :meth:`put_zone_ipv6s` are not implemented.

        This function should replace the AAAA records for the given domain with
        the records provided. If this provider's API requires using the
        original FQDN (rather than separate subdomain and zone fields), use
        :meth:`fqdn_of` on the parameters to obtain it.

        This will only be called for the domains Ruddr is configured to update.

        :param subdomain: The subdomain to publish the records for (only the
                          subdomain portion), empty for the root domain of the
                          zone
        :param zone: The zone the subdomain belongs to
        :param addresses: The addresses for the new records
        :param ttl: The TTL for the new records (or ``None`` if the
                    ``fetch_*_ipv6s`` functions didn't provide any). Ruddr
                    passes this through unchanged.

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    def _get_subdomain_and_zone_for(
        self,
        fqdn: str,
        zones: Optional[List[str]],
    ) -> Tuple[str, str]:
        """Find the zone the FQDN belongs to and return that and the subdomain
        portion.

        If a zone list is given, use that to determine the FQDN's zone (and
        verify that the zone is present). If not, use the `publix suffix list`_
        to determine the zone.

        .. _public suffix list: https://publicsuffix.org/

        :param fqdn: Domain name to split into subdomain and zone
        :param zones: List of zones, or ``None``

        :return: A 2-tuple ``(subdomain, zone)``
        :raise PublishError: if the given FQDN is not in any of the given zones
        """
        if zones is None:
            # Use public suffix list
            if self._zone_splitter is None:
                self._zone_splitter = ZoneSplitter(self._datadir)
            return self._zone_splitter.split(fqdn)

        for zone in zones:
            try:
                subdomain = self.subdomain_of(fqdn, zone)
            except ValueError:
                continue
            return (subdomain, zone)
        self.log.error("Domain '%s' not in any available zone")
        raise PublishError(f"Domain {fqdn} not in any zone available to "
                           f"updater {self.name}")

    def _get_hosts_by_zone(self) -> Dict[str, List[str]]:
        """Get a list of subdomains to be updated, sorted into zones

        :return: A dict with zones as keys and lists of subdomains as values,
                 with the root of the zone represented by an empty string
        """
        self.log.debug("Assembling a dict of hosts by zone")
        result = dict()
        zones_fetched = False
        zones = None

        for host, zone in self._hosts:
            if zone is None:
                if not zones_fetched:
                    self.log.debug("Fetching zones")
                    try:
                        self.get_zones()
                    except NotImplementedError:
                        self.log.debug("get_zones() not implemented, will use"
                                       "PSL")
                subdomain, zone = self._get_subdomain_and_zone_for(host, zones)
            else:
                subdomain = self.subdomain_of(host, zone)
            result.setdefault(zone, []).append(subdomain)

        return result

    def _verify_and_group_addrs_by_host(
        self,
        zone: str,
        records: List[Tuple[str, Addr, Optional[int]]],
        hosts: List[str],
    ) -> Dict[str, Tuple[List[Addr], Optional[int]]]:
        """Group the list of records by host and verify that at least one
        record is present for each listed host

        :param zone: The zone the records are from
        :param records: A list of records from :func:`fetch_zone_ipv4s` or
                        :func:`fetch_zone_ipv6s`
        :param hosts: A list of subdomains
        :return: Records grouped by host: a :class:`dict` where keys are the
                 subdomain and values are 2-tuples ``(addrs, ttl)`` where
                 ``addrs`` is a list of :class:`~ipaddress.IPv4Address` or
                 :class:`~ipaddress.IPv6Address` and ``ttl`` is the lowest TTL
                 of all the given records for that subdomain.
        :raises PublishError: if any host is missing from the records
        """
        result = dict()
        for next_host, next_addr, next_ttl in records:
            if next_host in result:
                addrs, ttl = result[next_host]
                addrs.append(next_addr)
                if next_ttl is not None and (ttl is None or ttl > next_ttl):
                    ttl = next_ttl
                result[next_host] = addrs, ttl
            else:
                result[next_host] = [next_addr], next_ttl

        for host in hosts:
            if host not in result:
                self.log.error("No A record for subdomain %s in zone %s",
                               host, zone)
                raise PublishError(f"Updater {self.name} found no A records "
                                   f"for subdomain {host} in zone {zone}")

        return result

    def _get_ipv4_records(
        self,
        zone: str,
        subdomains: List[str],
    ) -> Tuple[
        Dict[str, Tuple[List[ipaddress.IPv4Address], Optional[int]]],
        Union[bool, PublishError]
    ]:
        """Get A records, group by subdomain, and return whether they could be
        fetched by zone. Can also return a :exc:`PublishError` as the second
        element in the tuple, indicating it was not fetched by zone and at
        least one :exc:`PublishError` occurred (:exc:`PublishError` while
        fetching by zone is simply raised because there can't be partial
        success in that case)

        :param zone: Zone to fetch records for
        :param subdomains: Subdomains to fetch
        :return: ``(records_by_subdomain, by_zone|PublishError)``
        :raises PublishError: if there was a problem fetching records
        :raises FatalPublishError: if necessary methods are not implemented
        """
        # First try using fetch_zone_ipv4s
        try:
            records = self.fetch_zone_ipv4s(zone)
        except NotImplementedError:
            self.log.debug("fetch_zone_ipv4s not implemented, will fall "
                           "back to fetching by domain")
        else:
            records = self._verify_and_group_addrs_by_host(zone, records,
                                                           subdomains)
            return records, True

        # Use fetch_subdomain_ipv4s if it didn't work
        records = dict()
        error = None
        for subdomain in subdomains:
            try:
                domain_records = self.fetch_subdomain_ipv4s(subdomain, zone)
            except NotImplementedError:
                self.log.critical("Updater has a bug: Neither fetch_zone_ipv4s"
                                  " nor fetch_subdomain_ipv4s is implemented")
                raise FatalPublishError("Neither fetch_zone_ipv4s nor "
                                        "fetch_subdomain_ipv4s is implemented "
                                        f"for updater {self.name}")
            except PublishError as e:
                # Subclass should already log, so use debug here
                self.log.debug("Could not fetch A records for domain "
                               f"{self.fqdn_of(subdomain, zone)}: %s", e)
                if error is None:
                    error = e
                continue

            ttl = min((rec[1] for rec in domain_records if rec[1] is not None),
                      default=None)
            domain_record_addrs = [rec[0] for rec in domain_records]
            records[subdomain] = (domain_record_addrs, ttl)
        if error is None:
            return records, False
        else:
            return records, error

    def _put_ipv4_records(
        self,
        zone: str,
        subdomains: List[str],
        records: Dict[str, Tuple[List[ipaddress.IPv4Address], Optional[int]]],
        by_zone: bool,
    ):
        """Publish the given IPv4 records by zone or by domain

        :param zone: The zone the records are for
        :param subdomains: List of subdomains that must be published
        :param records: The records to publish, grouped by domain
        :param by_zone: Whether to publish by zone or by domain
        :raises PublishError: if publishing fails
        """
        if by_zone:
            try:
                self.put_zone_ipv4s(zone, records)
            except NotImplementedError:
                self.log.debug("put_zone_ipv4s not implemented, will fall back"
                               " to publishing by domain")
            else:
                return

        error = None
        for subdomain in subdomains:
            if subdomain not in records:
                self.log.debug("Skipping ipv4 update for %s with no existing A"
                               " records", self.fqdn_of(subdomain, zone))
                continue
            if len(records[subdomain][0]) != 1:
                self.log.critical("Bug in updater (incorrect number of A "
                                  "records)")
                raise FatalPublishError(f"Bug in updater {self.name}")
            address = records[subdomain][0][0]
            ttl = records[subdomain][1]
            try:
                self.put_subdomain_ipv4(subdomain, zone, address, ttl)
            except NotImplementedError:
                self.log.critical("Updater has a bug: put_subdomain_ipv4 must "
                                  "be implemented and is not")
                raise FatalPublishError("put_subdomain_ipv4 must be "
                                        f"implemented for updater {self.name} "
                                        "and is not")
            except PublishError as e:
                # Subclass should already log, so use debug here
                self.log.debug("Could not put A record for domain "
                               f"{self.fqdn_of(subdomain, zone)}: %s", e)
                if error is None:
                    error = e
                continue
        if error is not None:
            raise error

    def publish_ipv4(self, address: ipaddress.IPv4Address):
        """:meta private:"""
        hosts_by_zone = self._get_hosts_by_zone()

        error = None
        for zone, subdomains in hosts_by_zone.items():
            # Fetch zone's records
            self.log.debug("Fetching A records")
            try:
                records, by_zone = self._get_ipv4_records(zone, subdomains)
            except PublishError as e:
                if error is None:
                    error = e
                continue
            if isinstance(by_zone, PublishError):
                if error is None:
                    error = by_zone
                by_zone = False

            # Update records
            for subdomain in subdomains:
                if subdomain in records:
                    ttl = records[subdomain][1]
                    records[subdomain] = ([address], ttl)
                elif by_zone:
                    fqdn = self.fqdn_of(subdomain, zone)
                    self.log.warning("Updater did not find A record for %s",
                                     fqdn)
                    if error is None:
                        error = PublishError(f"Updater {self.name} did not "
                                             "find A record for domain "
                                             f"{fqdn}")

            # Put zone's records
            self.log.debug("Putting A records")
            try:
                self._put_ipv4_records(zone, subdomains, records, by_zone)
            except PublishError as e:
                if error is None:
                    error = e
                continue

        if error is not None:
            raise error

    def _get_ipv6_records(
        self,
        zone: str,
        subdomains: List[str],
    ) -> Tuple[
        Dict[str, Tuple[List[ipaddress.IPv6Address], Optional[int]]],
        Union[bool, PublishError]
    ]:
        """Get AAAA records, group by subdomain, and return whether they could
        be fetched by zone. Can also return a :exc:`PublishError` as the
        second element in the tuple, indicating it was not fetched by zone and
        at least one :exc:`PublishError` occurred (:exc:`PublishError`
        while fetching by zone is simply raised because there can't be partial
        success in that case)

        :param zone: Zone to fetch records for
        :param subdomains: Subdomains to fetch
        :return: ``(records_by_subdomain, by_zone|PublishError)``
        :raises PublishError: if there was a problem fetching records
        :raises FatalPublishError: if necessary methods are not implemented
        """
        # First try using fetch_zone_ipv6s
        try:
            records = self.fetch_zone_ipv6s(zone)
        except NotImplementedError:
            self.log.debug("fetch_zone_ipv6s not implemented, will fall "
                           "back to fetching by domain")
        else:
            records = self._verify_and_group_addrs_by_host(zone, records,
                                                           subdomains)
            return records, True

        # Use fetch_subdomain_ipv6s if it didn't work
        records = dict()
        error = None
        for subdomain in subdomains:
            try:
                domain_records = self.fetch_subdomain_ipv6s(subdomain, zone)
            except NotImplementedError:
                self.log.critical("Updater has a bug: Neither fetch_zone_ipv6s"
                                  " nor fetch_subdomain_ipv6s is implemented")
                raise FatalPublishError("Neither fetch_zone_ipv6s nor "
                                        "fetch_subdomain_ipv6s is implemented "
                                        f"for updater {self.name}")
            except PublishError as e:
                # Subclass should already log, so use debug here
                self.log.debug("Could not fetch AAAA records for domain "
                               f"{self.fqdn_of(subdomain, zone)}: %s", e)
                if error is None:
                    error = e
                continue

            ttl = min((rec[1] for rec in domain_records if rec[1] is not None),
                      default=None)
            domain_record_addrs = [rec[0] for rec in domain_records]
            records[subdomain] = (domain_record_addrs, ttl)
        if error is None:
            return records, False
        else:
            return records, error

    def _put_ipv6_records(
        self,
        zone: str,
        subdomains: List[str],
        records: Dict[str, Tuple[List[ipaddress.IPv6Address], Optional[int]]],
        by_zone: bool,
    ):
        """Publish the given IPv6 records by zone or by domain

        :param zone: The zone the records are for
        :param subdomains: List of subdomains that must be published
        :param records: The records to publish, grouped by domain
        :param by_zone: Whether to publish by zone or by domain
        :raises PublishError: if publishing fails
        """
        if by_zone:
            try:
                self.put_zone_ipv6s(zone, records)
            except NotImplementedError:
                self.log.debug("put_zone_ipv6s not implemented, will fall back"
                               " to publishing by domain")
            else:
                return

        error = None
        for subdomain in subdomains:
            if subdomain not in records:
                self.log.debug("Skipping ipv6 update for %s with no existing "
                               "AAAA records", self.fqdn_of(subdomain, zone))
                continue
            addresses = records[subdomain][0]
            ttl = records[subdomain][1]
            try:
                self.put_subdomain_ipv6s(subdomain, zone, addresses, ttl)
            except NotImplementedError:
                self.log.critical("Updater has a bug: put_subdomain_ipv6s must"
                                  " be implemented and is not")
                raise FatalPublishError("put_subdomain_ipv6s must be "
                                        f"implemented for updater {self.name} "
                                        "and is not")
            except PublishError as e:
                # Subclass should already log, so use debug here
                self.log.debug("Could not put AAAA record for domain "
                               f"{self.fqdn_of(subdomain, zone)}: %s", e)
                if error is None:
                    error = e
                continue
        if error is not None:
            raise error

    def publish_ipv6(self, network: ipaddress.IPv6Network):
        """:meta private:"""
        hosts_by_zone = self._get_hosts_by_zone()

        error = None
        for zone, subdomains in hosts_by_zone.items():
            # Fetch zone's records
            self.log.debug("Fetching AAAA records")
            try:
                records, by_zone = self._get_ipv6_records(zone, subdomains)
            except PublishError as e:
                if error is None:
                    error = e
                continue
            if isinstance(by_zone, PublishError):
                if error is None:
                    error = by_zone
                by_zone = False

            # Update records
            for subdomain in subdomains:
                if subdomain in records:
                    ttl = records[subdomain][1]
                    addrs = records[subdomain][0]
                    addrs = [self.replace_ipv6_prefix(network, addr)
                             for addr in addrs]
                    records[subdomain] = (addrs, ttl)
                elif by_zone:
                    fqdn = self.fqdn_of(subdomain, zone)
                    self.log.warning("Updater did not find AAAA record for %s",
                                     fqdn)
                    if error is None:
                        error = PublishError(f"Updater {self.name} did not "
                                             "find AAAA record for domain "
                                             f"{fqdn}")

            # Put zone's records
            self.log.debug("Putting AAAA records")
            try:
                self._put_ipv6_records(zone, subdomains, records, by_zone)
            except PublishError as e:
                if error is None:
                    error = e
                continue

        if error is not None:
            raise error

    @staticmethod
    def subdomain_of(fqdn: str, zone: str) -> str:
        """Return the subdomain portion of the given FQDN.

        :param fqdn: The FQDN to get the subdomain of (*without* trailing dot)
        :param zone: The zone this FQDN belongs to (empty for root zone)

        :return: The subdomain portion, e.g. "foo.bar" for FQDN
                 "foo.bar.example.com" with zone "example.com", or the empty
                 string if the FQDN is the zone's root domain
        :raises ValueError: if the FQDN is not in the given zone
        """
        if zone == '':
            return fqdn
        if not fqdn.endswith(zone):
            raise ValueError(f"'{fqdn}' not in zone '{zone}'")
        result = fqdn[: -len(zone)]
        if result == '':
            return ''
        if result[-1] != '.':
            raise ValueError(f"'{fqdn}' not in zone '{zone}'")
        return result.rstrip('.')

    @staticmethod
    def fqdn_of(subdomain: str, zone: str) -> str:
        """Return an FQDN for the given subdomain in the given zone.

        :param subdomain: The subdomain to return an FQDN for, or the empty
                          string for the zone's root domain
        :param zone: The zone the subdomain resides in (empty for root zone)

        :return: An FQDN, without trailing dot
        """
        if subdomain == '':
            return zone
        elif zone == '':
            return subdomain
        else:
            return f'{subdomain}.{zone}'


class TwoWayUpdater(TwoWayZoneUpdater):
    """Base class for updaters supporting protocols that are two-way and *not*
    zone-based, that is:

    - The API supports fetching the current address(es) for hosts, either
      individually or by fetching all domains in the account
    - The API has no concept of zones, meaning there are not zone-related API
      calls, nor is the zone required as a parameter for any other operation

    It's meant to be flexible enough for a variety of API styles. For example,
    most APIs will allow fetching and updating individual domains, but some
    may only provide a way to fetch or update all domains in the account at
    once. Still others may be a hybrid, requiring you to fetch all domains in
    the account but update domains individually. This class supports all of the
    above by allowing only the appropriate methods to be implemented.

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param datadir: The configured data directory
    """

    def __init__(self, name: str, addrfile: Addrfile, datadir: str):
        super().__init__(name, addrfile, datadir)

    def init_hosts(self, hosts: Union[List[str], str]):
        """Provide the list of hosts to be updated.

        This is separate from :meth:`__init__` so subclasses can rely on the
        logger while doing their config parsing, then pass the list of hosts
        in via this method after. **It must be called before your subclass's
        constructor completes.**

        The list can be provided either as an unparsed :class:`str` with a
        whitespace-separated list of domain names or as an actual :class:`list`
        of domain names.

        :param hosts: The list of hosts to be updated
        :raises ConfigError: if there is a duplicated
        """
        if isinstance(hosts, str):
            hosts = hosts.split()
        # Put every host in root zone
        super().init_hosts_and_zones([(host, '') for host in hosts])

    @abstractmethod
    def fetch_all_ipv4s(
        self
    ) -> List[Tuple[str, ipaddress.IPv4Address, Optional[int]]]:
        """Get a list of all A (IPv4) records in the account.

        **Implementing this method in subclasses is optional.** If not
        implemented, then :meth:`fetch_domain_ipv4s` and
        :meth:`put_domain_ipv4` must be implemented.

        If implemented, this function should return a list of A (IPv4) records
        in the form ``(domain, addr, ttl)`` where ``domain`` is the domain
        name for the record, ``addr`` is an :class:`~ipaddress.IPv4Address`,
        and ``ttl`` is the TTL of the record.

        The ``ttl`` may be set to ``None`` if the API does not provide it. It
        is only required for providers that would change the TTL back to
        default if it's not explicitly included when Ruddr later updates the
        record.

        If there are multiple records/IPv4s for a single domain, return them as
        separate list items with the same ``domain``. Note that if the domain
        needs to be updated by Ruddr, it will only produce a single record to
        replace them.

        :return: A list of A records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or the
                              zone does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_all_ipv6s(
        self
    ) -> List[Tuple[str, ipaddress.IPv6Address, Optional[int]]]:
        """Get a list of all AAAA (IPv6) records in the account.

        **Implementing this method in subclasses is optional.** If not
        implemented, then :meth:`fetch_domain_ipv6s` and
        :meth:`put_domain_ipv6s` must be implemented.

        If implemented, this function should return a list of AAAA (IPv6)
        records in the form ``(domain, addr, ttl)`` where ``domain`` is the
        domain name for the record, ``addr`` is an
        :class:`~ipaddress.IPv6Address`, and ``ttl`` is the TTL of the record.

        The ``ttl`` may be set to ``None`` if the API does not provide it. It
        is only required for providers that would change the TTL back to
        default if it's not explicitly included when Ruddr later updates the
        record.

        If there are multiple records/IPv6s for a single domain, return them as
        separate list items with the same ``domain``. If the domain needs to be
        updated by Ruddr, it will update all of them.

        :return: A list of AAAA records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or the
                              zone does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_domain_ipv4s(
        self,
        domain: str,
    ) -> List[Tuple[ipaddress.IPv4Address, Optional[int]]]:
        """Get a list of A (IPv4) records for the given domain.

        **Implementing this method in subclasses is optional.** It only needs
        to be implemented if :meth:`fetch_all_ipv4s` is not implemented.

        This function should return a list of A (IPv4) records for the given
        domain. The return value is a list of tuples ``(addr, ttl)`` where
        ``addr`` is an :class:`~ipaddress.IPv4Address` and ``ttl`` is the TTL
        of the record.

        The ``ttl`` may be set to ``None`` if the API does not provide it. It
        is only required for providers that would change the TTL back to
        default if it's not explicitly included when Ruddr later updates the
        record.

        The return value is a list in case there is more than one A record
        associated with the domain; however, note that Ruddr will want to
        replace all of them with a single record.

        :param domain: The domain to fetch records for

        :return: A list of A records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or no
                              such record exists
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_domain_ipv6s(
        self,
        domain: str,
    ) -> List[Tuple[ipaddress.IPv6Address, Optional[int]]]:
        """Get a list of AAAA (IPv6) records for the given domain.

        **Implementing this method in subclasses is optional.** It only needs
        to be implemented if :meth:`fetch_all_ipv6s` is not implemented.

        This function should return a list of AAAA (IPv6) records for the
        given domain. The return value is a list of tuples ``(addr, ttl)``
        where ``addr`` is an :class:`~ipaddress.IPv6Address` and ``ttl`` is the
        TTL of the record.

        The ``ttl`` may be set to ``None`` if the API does not provide it. It
        is only required for providers that would change the TTL back to
        default if it's not explicitly included when Ruddr later updates the
        record.

        The return value is a list in case there is more than one AAAA record
        associated with the domain. Ruddr will update all of them.

        :param domain: The domain to fetch records for

        :return: A list of AAAA records in the format described

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure, or no
                              such record exists
        """
        raise NotImplementedError

    @abstractmethod
    def put_all_ipv4s(
        self,
        records: Dict[str, Tuple[List[ipaddress.IPv4Address], Optional[int]]],
    ):
        """Publish A (IPv4) records for the account.

        **Implementing this method in subclasses is optional.** However, either
        this function or :meth:`put_domain_ipv4` must be implemented. The
        latter must be implemented if :meth:`fetch_all_ipv4s` is not
        implemented.

        If implemented, this function should replace all the A (IPv4) records
        in the account with the records provided. The records are provided as a
        :class:`dict` where the keys are the domain names and the values are
        2-tuples ``(addrs, ttl)`` where ``addrs`` is a list of
        :class:`~ipaddress.IPv4Address` and ``ttl`` is an :class:`int` (or
        ``None`` if the :meth:`fetch_all_ipv4s` function didn't provide any).

        Records that Ruddr is not configured to update will be passed through
        from :meth:`fetch_all_ipv4s` unmodified.

        :param records: The records to publish

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    @abstractmethod
    def put_all_ipv6s(
        self,
        records: Dict[str, Tuple[List[ipaddress.IPv6Address], Optional[int]]],
    ):
        """Publish AAAA (IPv6) records for the account.

        **Implementing this method in subclasses is optional.** However, either
        this function or :meth:`put_domain_ipv6s` must be implemented. The
        latter must be implemented if :meth:`fetch_all_ipv6s` is not
        implemented.

        If implemented, this function should replace all the AAAA (IPv6)
        records in the account with the records provided. The records are
        provided as a :class:`dict` where the keys are the domain names and the
        values are 2-tuples ``(addrs, ttl)`` where ``addrs`` is a list of
        :class:`~ipaddress.IPv6Address` and ``ttl`` is an :class:`int` (or
        ``None`` if the :meth:`fetch_all_ipv6s` function didn't provide any).

        Records that Ruddr is not configured to update will be passed through
        from :meth:`fetch_all_ipv6s` unmodified.

        :param records: The records to publish

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    @abstractmethod
    def put_domain_ipv4(self, domain: str,
                        address: ipaddress.IPv4Address, ttl: Optional[int]):
        """Publish an A (IPv4) record for the given domain.

        **Implementing this method in subclasses is optional.** However, it
        must be implemented if either :meth:`fetch_all_ipv4s` or
        :meth:`put_all_ipv4s` are not implemented.

        This function should replace the A (IPv4) records for the given domain
        with a single A record matching the given parameters.

        This will only be called for the domains Ruddr is configured to update.

        :param domain: The domain to publish the record for
        :param address: The address for the new record
        :param ttl: The TTL for the new record (or ``None`` if the
                    ``fetch_*_ipv4s`` functions didn't provide any). Ruddr
                    passes this through unchanged.

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    @abstractmethod
    def put_domain_ipv6s(self, domain: str,
                         addresses: List[ipaddress.IPv6Address],
                         ttl: Optional[int]):
        """Publish AAAA (IPv6) records for the given domain.

        **Implementing this method in subclasses is optional.** However, it
        must be implemented if either :meth:`fetch_all_ipv6s` or
        :meth:`put_all_ipv6s` are not implemented.**

        This function should replace the AAAA (IPv6) records for the given
        domain with the records provided.

        This will only be called for the domains Ruddr is configured to update.

        :param domain: The domain to publish the records for
        :param addresses: The address for the new records
        :param ttl: The TTL for the new records (or ``None`` if the
                    ``fetch_*_ipv6s`` functions didn't provide any). Ruddr
                    passes this through unchanged.

        :raises NotImplementedError: if not implemented
        :raises PublishError: if implemented, but there is a failure
        """
        raise NotImplementedError

    def fetch_zone_ipv4s(
        self,
        zone: str,
    ) -> List[Tuple[str, ipaddress.IPv4Address, Optional[int]]]:
        """:meta private:"""
        assert zone == ''
        return self.fetch_all_ipv4s()

    def fetch_subdomain_ipv4s(
        self,
        subdomain: str,
        zone: str,
    ) -> List[Tuple[ipaddress.IPv4Address, Optional[int]]]:
        """:meta private:"""
        assert zone == ''
        return self.fetch_domain_ipv4s(subdomain)

    def put_zone_ipv4s(
        self,
        zone: str,
        records: Dict[str, Tuple[List[ipaddress.IPv4Address], Optional[int]]]
    ):
        """:meta private:"""
        assert zone == ''
        self.put_all_ipv4s(records)

    def put_subdomain_ipv4(self, subdomain: str, zone: str,
                           address: ipaddress.IPv4Address, ttl: Optional[int]):
        """:meta private:"""
        assert zone == ''
        self.put_domain_ipv4(subdomain, address, ttl)

    def fetch_zone_ipv6s(
        self,
        zone: str
    ) -> List[Tuple[str, ipaddress.IPv6Address, Optional[int]]]:
        """:meta private:"""
        assert zone == ''
        return self.fetch_all_ipv6s()

    def fetch_subdomain_ipv6s(
        self,
        subdomain: str,
        zone: str
    ) -> List[Tuple[ipaddress.IPv6Address, Optional[int]]]:
        """:meta private:"""
        assert zone == ''
        return self.fetch_domain_ipv6s(subdomain)

    def put_zone_ipv6s(
        self,
        zone: str,
        records: Dict[str, Tuple[List[ipaddress.IPv6Address], Optional[int]]]
    ):
        """:meta private:"""
        assert zone == ''
        self.put_all_ipv6s(records)

    def put_subdomain_ipv6s(self, subdomain: str, zone: str,
                            addresses: List[ipaddress.IPv6Address],
                            ttl: Optional[int]):
        """:meta private:"""
        assert zone == ''
        self.put_domain_ipv6s(subdomain, addresses, ttl)


class OneWayUpdater(Updater):
    """Base class for updaters supporting protocols that are one-way, that is,
    the API has no way to obtain the current address for a host. Ruddr requires
    the current address for IPv6 updates since it only updates the prefix. This
    class handles that requirement either by using hardcoded IPv6 addresses or
    by looking up the current IPv6 address in DNS.

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    """

    def __init__(
        self,
        name,
        addrfile,
    ):
        super().__init__(name, addrfile)

        #: A list of hosts and how to get the host portion of their IPv6s
        self._hosts: List[
            Tuple[str, Union[str, ipaddress.IPv6Address, None]]
        ] = []

        #: Nameserver to use when looking up AAAA records for FQDNs in hosts
        self._nameserver = None

    def init_params(
        self,
        hosts: Union[
            List[Tuple[str, Union[ipaddress.IPv6Address, str, None]]],
            str
        ],
        nameserver: Optional[str] = None,
        min_retry=300
    ):
        """Initialize the hosts list, nameserver, and min retry interval.

        This is separate from :meth:`__init__` so subclasses can rely on the
        logger while doing their config parsing, then pass the relevant config
        options in by calling this method. **It must be called before your
        subclass's constructor completes.**

        :param hosts: A list of 2-tuples ``(hostname, ipv6_src)`` specifying
                      which hosts should be updated and where their IPv6
                      addresses should come from. ``ipv6_src`` can be an
                      :class:`~ipaddress.IPv6Address` to hardcode the host
                      portion of the address, a :class:`str` containing an FQDN
                      to look up in DNS, or ``None`` if this host should not
                      get IPv6 updates at all. Alternatively, this entire
                      parameter may be in unparsed string form—see the docs for
                      the ``standard`` updater for the expected format.
        :param nameserver: The nameserver to use to look up AAAA records for
                           the FQDNs, if any. If ``None``, system DNS is used.
        :param min_retry: The minimum retry interval after failed updates, in
                          seconds. (There is an exponential backoff for
                          subsequent retries.)
        """
        if isinstance(hosts, str):
            self._hosts = self._split_hosts(hosts)
        else:
            self._hosts = hosts

        self._nameserver = nameserver

        self.min_retry_interval = min_retry

    def _split_hosts(
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
        """:meta private:"""
        error = None
        for host, _ in self._hosts:
            try:
                self.publish_ipv4_one_host(host, address)
            except PublishError as e:
                if error is None:
                    error = e
        if error is not None:
            raise error

    @abstractmethod
    def publish_ipv4_one_host(self,
                              hostname: str,
                              address: ipaddress.IPv4Address):
        """Attempt to publish an IPv4 address for the given host.

        **Must be implemented by subclasses.**

        :param hostname: The host to publish for
        :param address: The address to publish

        :raise PublishError: if publishing fails (will automatically retry
                             after a delay)
        :raise FatalPublishError: if publishing fails in a non-recoverable way
                                  (all future publishing will halt)
        """
        raise NotImplementedError

    def publish_ipv6(self, network):
        """:meta private:"""
        error = None
        for host, ip_lookup in self._hosts:
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
        :exc:`PublishError`.

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
                               "for %s (for host %s): %s",
                               ip_lookup, hostname, e)
                raise PublishError(f"Updater {self.name} could not look up "
                                   f"the current IPv6 address for {ip_lookup}")
            if current_ipv6 is None:
                self.log.error("DNS lookup for %s (for host %s) returned no "
                               "IPv6 addresses", ip_lookup, hostname)
                raise PublishError(f"Updater {self.name} got no IPv6 when "
                                   f"looking up {ip_lookup}")
            self.log.debug("Looked up IPv6 addr %s for hostname %s (with DN "
                           "%s)", current_ipv6.compressed, hostname, ip_lookup)
        return current_ipv6

    def _lookup_ipv6(self, ip_lookup: str) -> Optional[ipaddress.IPv6Address]:
        """Do a DNS lookup for an AAAA record, preferring globally-routable
        addresses if multiple are present

        :raises OSError: if lookup failed
        :raises dns.exception.DNSException: if lookup failed
        :return: An :class:`~ipaddress.IPv6Address` or ``None`` if none could
                 be found
        """
        if self._nameserver is None:
            self.log.debug("Looking up AAAA record(s) for '%s' in system DNS",
                           ip_lookup)
            results = socket.getaddrinfo(ip_lookup, None,
                                         family=socket.AF_INET6)
            aaaa_records = [
                ipaddress.IPv6Address(ai[4][0]) for ai in results
            ]
        else:
            self.log.debug("Looking up address of nameserver %s",
                           self._nameserver)
            ns_results = socket.getaddrinfo(self._nameserver, 53,
                                            type=socket.SOCK_DGRAM)
            ns_list = [ai[4][0] for ai in ns_results]
            self.log.debug("Found address(es) for nameserver %s: %s",
                           self._nameserver, str(ns_list))

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

    @abstractmethod
    def publish_ipv6_one_host(self,
                              hostname: str,
                              address: ipaddress.IPv6Address):
        """Attempt to publish an IPv6 address for the given host.

        **Must be implemented by subclasses.**

        :param hostname: The host to publish for
        :param address: The address to publish

        :raise PublishError: if publishing fails (will automatically retry
                             after a delay)
        :raise FatalPublishError: if publishing fails in a non-recoverable way
                                  (all future publishing will halt)
        """
        raise NotImplementedError
