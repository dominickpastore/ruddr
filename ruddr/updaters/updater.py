"""Base class for Ruddr updaters"""

import functools
import ipaddress
import logging
import threading
import types

from ..exceptions import PublishError, FatalPublishError


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
