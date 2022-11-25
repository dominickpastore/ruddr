"""Base class for Ruddr updaters"""

import functools
import ipaddress
import logging
import threading
import types

from ..exceptions import PublishError


class _Retry:
    """A decorator that makes a function retry periodically until success.
    Success is defined by not raising :exc:`~ruddr.PublishError`. The first
    retry interval is 5 minutes, with exponential backoff until the retry
    interval reaches 1 day, at which point it will remain constant.

    Assumes it is being applied to a method of :class:`~ruddr.Updater`. Other
    uses may not work as intended."""

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
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
        except PublishError:
            if self.retries <= 8:
                # Retry after 5 minutes the first time, doubling each retry
                retry_delay = 300 * 2 ** self.retries
            else:
                # Cap retry time at one day
                retry_delay = 86400
            self.retries += 1
            obj.log.info("Update failed. Retrying in %d minutes.",
                         retry_delay // 60)
            timer = threading.Timer(retry_delay, self.retry,
                                    args=(seq, obj, *args), kwargs=kwargs)
            timer.daemon = True
            timer.start()


class Updater:
    """Base class for Ruddr updaters. Handles setting up logging, attaching to
    a notifier, retries, and working with the addrfile.

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    """

    def __init__(self, name, addrfile):
        #: Updater name (from config section heading)
        self.name = name

        #: Logger (see standard :mod:`logging` module)
        self.log = logging.getLogger(f'ruddr.updater.{self.name}')

        self.addrfile = addrfile

    @_Retry
    def update_ipv4(self, address):
        """Receive a new IPv4 address from the attached notifier. If it does
        not match the current address, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv4Address` to update with
        """
        if not self.addrfile.needs_ipv4_update(self.name, address):
            self.log.info("Skipping update as %s is current address",
                          address.exploded)
            return

        # Invalidate current address before publishing. If publishing fails,
        # current address is indeterminate.
        self.addrfile.invalidate_ipv4(self.name, address)

        try:
            self.publish_ipv4(address)
        except PublishError:
            if address is None:
                self.log.error("Failed to unpublish IPv4 address")
            else:
                self.log.error("Failed to publish address %s", address)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv4 updates")
            return

        self.addrfile.set_ipv4(self.name, address)

    @_Retry
    def update_ipv6(self, address):
        """Receive a new IPv6 prefix from the attached notifier. If it does
        not match the current prefix, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv6Network` to update with
        """
        if not self.addrfile.needs_ipv6_update(self.name, address):
            self.log.info("Skipping update as %s is current address",
                          address.compressed)
            return

        # Invalidate current address before publishing. If publishing fails,
        # current address is indeterminate.
        self.addrfile.invalidate_ipv6(self.name, address)

        try:
            self.publish_ipv6(address)
        except PublishError:
            if address is None:
                self.log.error("Failed to unpublish IPv6 address")
            else:
                self.log.error("Failed to publish address %s", address)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv6 updates")
            return

        self.addrfile.set_ipv6(self.name, address)

    def publish_ipv4(self, address):
        """Publish a new IPv4 address to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        Must be implemented by subclasses if they support IPv4 updates. Be sure
        to raise :exc:`~ruddr.PublishError` when publishing fails!

        :param address: :class:`IPv4Address` to publish
        :raise PublishError: when publishing fails
        """
        raise NotImplementedError("IPv4 publish function not provided")

    def publish_ipv6(self, network):
        """Publish a new IPv6 prefix to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        Must be implemented by subclasses if they support IPv6 updates. Be sure
        to raise :exc:`~ruddr.PublishError` when publishing fails!

        :param network: :class:`IPv6Network` with the prefix to publish
        :raise PublishError: when publishing fails
        """
        raise NotImplementedError("IPv6 publish function not provided")
