"""Base class for Ruddr updaters"""

import functools
import logging
import threading
import types

from ..exceptions import ConfigError, PublishError


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
    :param manager: The DDNSManager
    :param global_config: Dict of ``[ruddr]`` config options
    :param config: Dict of config options for this updater
    """

    def __init__(self, name, manager, global_config, config):
        #: Updater name (from config section heading)
        self.name = name

        #: Logger (see standard :mod:`logging` module)
        self.log = logging.getLogger(f'ruddr.updater.{self.name}')

        self.manager = manager

        #: Most recent IPv4Address successfully updated
        self.ipv4 = manager.addrfile_get_ipv4(self.name)
        #: Most recent IPv6Address successfully updated
        self.ipv6 = manager.addrfile_get_ipv6(self.name)

        self._attach_notifiers(global_config, config)

    def _get_notifier_names(self, global_config, config):
        """Get the notifier name(s) from the config"""
        ipv4_notifier = None
        ipv6_notifier = None
        try:
            ipv4_notifier = config['notifier4']
        except KeyError:
            pass
        try:
            ipv6_notifier = config['notifier6']
        except KeyError:
            pass
        if ipv4_notifier is None:
            try:
                ipv4_notifier = config['notifier']
            except KeyError:
                pass
        if ipv6_notifier is None:
            try:
                ipv6_notifier = config['notifier']
            except KeyError:
                pass
        # If any notifiers are configured in the section for this updater,
        # ignore any globally configured notifiers
        if ipv4_notifier is not None or ipv6_notifier is not None:
            return (ipv4_notifier, ipv6_notifier)

        if ipv4_notifier is None:
            try:
                ipv4_notifier = global_config['notifier4']
            except KeyError:
                pass
        if ipv6_notifier is None:
            try:
                ipv6_notifier = global_config['notifier6']
            except KeyError:
                pass
        if ipv4_notifier is None:
            try:
                ipv4_notifier = global_config['notifier']
            except KeyError:
                pass
        if ipv6_notifier is None:
            try:
                ipv6_notifier = global_config['notifier']
            except KeyError:
                pass
        if ipv4_notifier is None and ipv6_notifier is None:
            raise ConfigError("No notifier is configured for updater %s and "
                              "there are no default notifiers configured"
                              % self.name)

        return (ipv4_notifier, ipv6_notifier)


    def _attach_notifiers(self, global_config, config):
        """Attach this updater to the configured notifier(s)"""
        ipv4_notifier_name, ipv6_notifier_name = self._get_notifier_names(
            global_config, config)

        if ipv4_notifier_name is not None:
            try:
                ipv4_notifier = self.manager.get_notifier(ipv4_notifier_name)
            except KeyError:
                raise ConfigError("Notifier %s does not exist" %
                                  ipv4_notifier_name) from None
            else:
                ipv4_notifier.attach_ipv4_updater(self.update_ipv4)

        if ipv6_notifier_name is not None:
            try:
                ipv6_notifier = self.manager.get_notifier(ipv6_notifier_name)
            except KeyError:
                raise ConfigError("Notifier %s does not exist" %
                                  ipv6_notifier_name) from None
            else:
                ipv4_notifier.attach_ipv6_updater(self.update_ipv6)

    @_Retry
    def update_ipv4(self, address):
        """Receive a new IPv4 address from the attached notifier. If it does
        not match the current address, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv4Address` to update with
        """
        if address == self.ipv4:
            self.log.info("Skipping update as %s is current address",
                          address.exploded)
            return

        # Set current address to None before publishing. If publishing fails,
        # current address is indeterminate.
        self.ipv4 = None
        manager.addrfile_set_ipv4(self.name, None)

        try:
            self.publish_ipv4(address)
        except PublishError:
            self.log.error("Failed to publish address %s", address.exploded)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv4 updates")
            return

        self.ipv4 = address
        manager.addrfile_set_ipv4(self.name, address)

    @_Retry
    def update_ipv6(self, address):
        """Receive a new IPv6 prefix from the attached notifier. If it does
        not match the current prefix, call the subclass' publish function,
        update the addrfile if successful, and retry if not.

        :param address: :class:`IPv6Network` to update with
        """
        if address == self.ipv6:
            self.log.info("Skipping update as %s is current address",
                          address.compressed)
            return

        # Set current address to None before publishing. If publishing fails,
        # current address is indeterminate.
        self.ipv6 = None
        manager.addrfile_set_ipv6(self.name, None)

        try:
            self.publish_ipv6(address)
        except PublishError:
            self.log.error("Failed to publish address %s", address.compressed)
            raise
        except NotImplementedError:
            self.log.debug("Updater does not implement IPv6 updates")
            return

        self.ipv6 = address
        manager.addrfile_set_ipv6(self.name, address)

    def publish_ipv4(self, address):
        """Publish a new IPv4 address to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        Must be implemented by subclasses if they support IPv4 updates. Be sure
        to raise :exc:`~ruddr.PublishError` when publishing fails!

        :param address: :class:`IPv4Address` to publish
        :raise PublishError` when publishing fails
        """
        raise NotImplementedError("IPv4 publish function not provided")

    def publish_ipv6(self, network):
        """Publish a new IPv6 prefix to the appropriate DDNS provider. Will
        only be called if an update contains a new address or a previous update
        failed.

        Must be implemented by subclasses if they support IPv6 updates. Be sure
        to raise :exc:`~ruddr.PublishError` when publishing fails!

        :param network: :class:`IPv6Network` with the prefix to publish
        :raise PublishError` when publishing fails
        """
        raise NotImplementedError("IPv6 publish function not provided")
