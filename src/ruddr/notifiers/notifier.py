"""Base class for Ruddr notifiers"""

import ipaddress
import logging
import threading
# Note: We are not using abstractmethod the way it is intended. We are using it
# purely to get Sphinx to mark methods as abstract. Thus, we intentionally do
# NOT use ABCMeta or inherit from ABC.
from abc import abstractmethod
from typing import Callable, Dict, List, Optional

from ruddr.exceptions import NotifyError, ConfigError, NotStartedError


class BaseNotifier:
    """Base class for all Ruddr notifiers. Sets up the logger, sets up some
    useful member variables, and handles attaching to update functions.

    Notifiers should generally not extend this class directly, but should
    extend :class:`Notifier` instead.

    :param name: Name of the notifier (from config section heading)
    :param config: Dict of config options for this notifier

    :raises ConfigError: if the configuration is invalid
    """

    def __init__(self, name: str, config: Dict[str, str]):
        #: Notifier name (from config section heading)
        self.name: str = name

        #: Logger (see standard :mod:`logging` module)
        self.log = logging.getLogger(f'ruddr.notifier.{self.name}')

        # Configuration options for all Notifiers:
        #
        # - skip_ipv4: default false
        #   If true, this notifier never checks or notifies for IPv4 addresses.
        #   Use when there is no IPv4 networking.
        #
        # - skip_ipv6: default false
        #   Like skip_ipv4, but for IPv6
        #
        # - ipv4_required: default true
        #   When true, failure to obtain the current IPv4 address is an error.
        #   When false, lack of IPv4 address is considered normal.
        #
        # - ipv6_required: default false
        #   Like ipv4_required, but for IPv6. Defaults to false since IPv6
        #   support in networks generally isn't universal.
        #
        # - skip_* options override *_required options
        #
        # Configuration suggestions:
        #
        # - Most people *can* get away with using the defaults, but it's best
        #   to be explicit if possible.
        #
        # - If IPv6 is known to be available, setting ipv6_required ensures
        #   that Ruddr will retry when it can't get a current IPv6 address.
        #
        # - If IPv6 is known to NOT be available, setting skip_ipv6 tells
        #   Ruddr not to waste time trying to determine an IPv6 address.

        try:
            self._skip_ipv4: bool = (config.get('skip_ipv4', 'false').lower()
                                     in ('true', 'on', 'yes', '1'))
        except ValueError:
            self.log.critical("'skip_ipv4' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'skip_ipv4' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")
        try:
            self._skip_ipv6: bool = (config.get('skip_ipv6', 'false').lower()
                                     in ('true', 'on', 'yes', '1'))
        except ValueError:
            self.log.critical("'skip_ipv6' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'skip_ipv6' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")

        if self._skip_ipv4 and self._skip_ipv6:
            self.log.critical("Cannot skip both IPv4 and IPv6")
            raise ConfigError(f"Notifier {self.name} cannot skip both IPv4 "
                              "and IPv6")

        try:
            self._ipv4_required: bool = (
                config.get('ipv4_required',
                           'false' if self._skip_ipv4 else 'true').lower()
                in ('true', 'on', 'yes', '1')
            )
        except ValueError:
            self.log.critical("'ipv4_required' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'ipv4_required' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")
        try:
            self._ipv6_required: bool = (config.get('ipv6_required',
                                                    'false').lower()
                                         in ('true', 'on', 'yes', '1'))
        except ValueError:
            self.log.critical("'ipv6_required' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'ipv6_required' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")

        if self._skip_ipv4 and self._ipv4_required:
            self.log.critical("Cannot require IPv4 when it is skipped")
            raise ConfigError(f"{self.name} updater cannot require IPv4 when "
                              "it is skipped")

        if self._skip_ipv6 and self._ipv6_required:
            self.log.critical("Cannot require IPv6 when it is skipped")
            raise ConfigError(f"{self.name} updater cannot require IPv6 when "
                              "it is skipped")

        self._ipv4_update_funcs: List[
            Callable[[ipaddress.IPv4Address], None]
        ] = []
        self._ipv6_update_funcs: List[
            Callable[[ipaddress.IPv6Network], None]
        ] = []

    def attach_ipv4_updater(
        self, update_func: Callable[[ipaddress.IPv4Address], None],
    ) -> None:
        """Attach an IPv4 update function to this notifier. No effect if IPv4
        is skipped for this notifier.

        :param update_func: A callable that accepts an :class:`IPv4Address` to
                            be called whenever the IPv4 address might have been
                            updated. It is the callee's responsibility to
                            ensure the update eventually happens successfully
                            (e.g. by scheduling a retry in a separate thread if
                            it fails), but this function should not block
                            longer than a single update attempt.
        :raises ConfigError: If config required for IPv4 notifying is missing
        """
        if self._skip_ipv4:
            self.log.info("Not attaching updater to notifier %s for skipped "
                          "IPv4", self.name)
            return
        self.log.debug("Attaching %s (IPv4) to notifier %s",
                       update_func.__name__, self.name)
        if len(self._ipv4_update_funcs) == 0 and not self.ipv4_ready():
            self.log.critical("Cannot use as IPv4 notifier without required "
                              "IPv4 config")
            raise ConfigError("Notifier %s cannot be an IPv4 notifier without "
                              "required IPv4 config" % self.name)
        self._ipv4_update_funcs.append(update_func)

    def attach_ipv6_updater(
        self, update_func: Callable[[ipaddress.IPv6Network], None]
    ) -> None:
        """Attach an IPv6 update function to this notifier. No effect if IPv6
        is skipped for this notifier.

        :param update_func: A callable that accepts an :class:`IPv6Network` to
                            be called whenever the IPv6 prefix might have been
                            updated. It is the callee's responsibility to
                            ensure the update eventually happens successfully
                            (e.g. by scheduling a retry in a separate thread if
                            it fails), but this function should not block
                            longer than a single update attempt.
        :raises ConfigError: If config required for IPv6 notifying is missing
        """
        if self._skip_ipv6:
            self.log.info("Not attaching updater to notifier %s for skipped "
                          "IPv6", self.name)
            return
        self.log.debug("Attaching %s (IPv6) to notifier %s",
                       update_func.__name__, self.name)
        if len(self._ipv6_update_funcs) == 0 and not self.ipv6_ready():
            self.log.critical("Cannot use as IPv6 notifier without required "
                              "IPv4 config")
            raise ConfigError("Notifier %s cannot be an IPv6 notifier without "
                              "required IPv6 config" % self.name)
        self._ipv6_update_funcs.append(update_func)

    def notify_ipv4(self, address: ipaddress.IPv4Address) -> None:
        """Subclasses must call this to notify all the attached IPv4 updaters
        of a (possibly) new IPv4 address.

        Subclasses may, but need not, call this if :meth:`want_ipv4` is false.

        :param address: The (possibly) new IPv4 address
        """
        self.log.debug("Notifier %s notifying attached updaters of IPv4 %s",
                       self.name, address.exploded)
        for update_func in self._ipv4_update_funcs:
            update_func(address)

    def notify_ipv6(self, prefix: ipaddress.IPv6Network) -> None:
        """Subclasses must call this to notify all the attached IPv6 updaters
        of a (possibly) new IPv6 prefix.

        Subclasses may, but need not, call this if :meth:`want_ipv6` is false.

        :param prefix: The (possibly) new IPv6 network prefix
        """
        self.log.debug("Notifier %s notifying attached updaters of IPv6 %s",
                       self.name, prefix.compressed)
        for update_func in self._ipv6_update_funcs:
            update_func(prefix)

    def want_ipv4(self) -> bool:
        """Subclasses should call this to determine whether to check for
        current IPv4 addresses at all.

        :return: ``True`` if so, ``False`` if not
        """
        # Will be true if no updaters are configured, or they weren't attached
        # because skip_ipv4
        return len(self._ipv4_update_funcs) > 0

    def want_ipv6(self) -> bool:
        """Subclasses should call this to determine whether to check for
        current IPv6 addresses at all.

        :return: ``True`` if so, ``False`` if not
        """
        # Will be true if no updaters are configured, or they weren't attached
        # because skip_ipv6
        return len(self._ipv6_update_funcs) > 0

    def need_ipv4(self) -> bool:
        """Subclasses must call this to determine if a lack of IPv4 addressing
        is an error.

        :return: ``True`` if so, ``False`` if not
        """
        return self.want_ipv4() and self._ipv4_required

    def need_ipv6(self) -> bool:
        """Subclasses must call this to determine if a lack of IPv6 addressing
        is an error.

        :return: ``True`` if so, ``False`` if not
        """
        return self.want_ipv6() and self._ipv6_required

    @abstractmethod
    def ipv4_ready(self) -> bool:
        """Check if all configuration required for IPv4 notifying is present.

        **Subclasses must override if there is any configuration only required
        for IPv4.**

        :return: ``True`` if so, ``False`` if not
        """
        return True

    @abstractmethod
    def ipv6_ready(self) -> bool:
        """Check if all configuration required for IPv6 notifying is present.

        **Subclasses must override if there is any configuration only required
        for IPv6.**

        :return: ``True`` if so, ``False`` if not
        """
        return True

    @abstractmethod
    def do_notify(self) -> None:
        """Check the IP address a single time and notify immediately, if
        possible.

        This is known as an "on-demand notify." Notifiers should support this
        if possible, but it is okay if they do not. In the latter case, this
        should do nothing and not raise any exceptions (except optionally
        :exc:`NotStartedError`).

        **Must be overridden by subclasses.**

        :raises NotStartedError: if the notifier is not started
        """
        raise NotImplementedError

    @abstractmethod
    def start(self) -> None:
        """Begin ongoing IP address notifications. Any setup should be complete
        before this function returns (e.g. opening socket connections, etc.)
        but ongoing notifications should continue in the background, e.g. on
        a separate thread.

        **Must be overridden by subclasses.**

        :raises NotifierSetupError: when there is a nonrecoverable error
                                    preventing notifier startup.
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Halt ongoing IP address notifications. Clean up gracefully and stop
        any non-daemon threads so Python may exit.

        This must not raise any exceptions, even if called before :meth:`start`
        or after :meth:`start` fails.

        **Must be overridden by subclasses.**
        """
        raise NotImplementedError


class Notifier(BaseNotifier):
    """A base class for notifiers. Supports a variety of notifier strategies,
    such as polling, event-based notifying, and hybrids. See the docs on
    :ref:`writing your own notifier <notifier_dev>` for more detail on what
    that means.

    Also handles setting up a logger, setting some useful member variables for
    subclasses, and attaching to update functions.

    :param name: Name of the notifier
    :param config: Dict of config options for this notifier

    :raises ConfigError: if the configuration is invalid
    """

    def __init__(self, name: str, config: Dict[str, str]):
        super().__init__(name, config)

        # See set_check_intervals for info on these
        self._retry_min_interval: int = 300
        self._retry_max_interval: int = 86400
        self._success_interval: int = 0

        self._lock: threading.RLock = threading.RLock()

        # Ensure can't do_notify, check, or stop when not started, or start
        # when already started. Must lock to access.
        self._started: bool = False

        # Used for retries and polling. Must lock to access.
        self._timer: Optional[threading.Timer] = None
        self._seq: int = 0
        self._retries: int = 0

        # For tests to join the thread doing the first check
        self.first_check = None

    def set_check_intervals(self,
                            retry_min_interval: int = 300,
                            retry_max_interval: int = 86400,
                            success_interval: int = 0,
                            config: Optional[Dict[str, str]] = None) -> None:
        """Set the retry intervals for the :meth:`check_once` function, and
        optionally set :meth:`check_once` to run periodically when successful.

        When :meth:`check_once` fails (by raising :exc:`NotifyError`), the next
        invocation will be scheduled using an exponential backoff strategy,
        starting with ``retry_min_interval`` seconds. Subsequent consecutive
        failures will be scheduled using successively longer intervals, until
        reaching the maximum failure interval, ``retry_max_interval`` seconds.

        The ``success_interval`` parameter triggers some additional behavior:

        - If ``success_interval`` is greater than zero, then when
          :meth:`check_once` succeeds, another invocation will be scheduled for
          ``success_interval`` seconds later. This is useful for notifiers that
          check the current address by polling, like the ``web`` notifier.
          Since :meth:`check` runs at notifier startup, that means
          :meth:`setup` and :meth:`teardown` may not have to be implemented at
          all for these polling-style notifiers.

        - If ``success_interval`` is zero, :meth:`check_once` will only be
          scheduled for future invocation for retries.

        If the ``config`` parameter is provided, it will be checked for keys
        ``retry_min_interval``, ``retry_max_interval``, and ``interval``. If
        either of the ``retry_*`` keys are found, their values override the
        parameters passed into this function. If the ``interval`` key is found,
        its value overrides the ``success_interval`` parameter *if and only if*
        the parameter was already nonzero (preventing a configuration mistake
        from changing a non-polling notifier into a polling notifier).

        In practice, that means this function should be called using the
        notifier's default values for ``retry_min_interval``,
        ``retry_max_interval``, and ``success_interval`` (if it needs defaults
        other than the method defaults) and passing in the config to allow
        the user to override them.

        **Subclasses should call this before returning from their
        constructor (if it needs to be called at all).**

        This has no effect if :meth:`check_once` raises
        :exc:`NotImplementedError`.

        :param retry_min_interval: Minimum retry interval
        :param retry_max_interval: Maximum retry interval
        :param success_interval: Normal polling interval, or 0
        :param config: Config dict for this updater

        :raises ConfigError: if the retry intervals are less than 1, the
                             success interval is less than 0, or the values in
                             the config cannot be converted to :class:`int`
        """
        self._retry_min_interval = retry_min_interval
        self._retry_max_interval = retry_max_interval

        if config is not None:
            try:
                self._retry_min_interval = int(config['retry_min_interval'])
            except KeyError:
                pass
            except ValueError:
                self.log.critical("'retry_min_interval' config option must be "
                                  "an integer > 0")
                raise ConfigError("'retry_min_interval' option for "
                                  f"{self.name} notifier must be an "
                                  "integer > 0")

            try:
                self._retry_max_interval = int(config['retry_max_interval'])
            except KeyError:
                pass
            except ValueError:
                self.log.critical("'retry_max_interval' config option must be "
                                  "an integer > 0")
                raise ConfigError("'retry_max_interval' option for "
                                  f"{self.name} notifier must be an "
                                  "integer > 0")

        if self._retry_min_interval <= 0:
            self.log.critical("'retry_min_interval' config option must be an "
                              "integer > 0")
            raise ConfigError(f"'retry_min_interval' option for {self.name} "
                              "notifier must be an integer > 0")

        if self._retry_max_interval <= 0:
            self.log.critical("'retry_max_interval' config option must be an "
                              "integer > 0")
            raise ConfigError(f"'retry_max_interval' option for {self.name} "
                              "notifier must be an integer > 0")

        self._success_interval = success_interval
        if self._success_interval == 0:
            return
        if config is not None:
            try:
                self._success_interval = int(config['interval'])
            except KeyError:
                pass
            except ValueError:
                self.log.critical("'interval' config option must be an "
                                  "integer >= 0")
                raise ConfigError(f"'interval' option for {self.name} "
                                  "notifier must be an integer > 0")

        if self._success_interval <= 0:
            self.log.critical("'interval' config option must be an "
                              "integer >= 0")
            raise ConfigError(f"'interval' option for {self.name} "
                              "notifier must be an integer > 0")

    def start(self) -> None:
        with self._lock:
            if self._started:
                self.log.warning("Not starting notifier: Already started")
                return

            try:
                self.setup()
            except NotImplementedError:
                self.log.info("Notifier has no setup")
                self._started = True
            else:
                self.log.info("Notifier is finished with setup")
                self._started = True

        # Do the first check in the background
        def first_check():
            try:
                self.check()
            except NotImplementedError:
                self.log.info("Not doing an immediate check as this notifier "
                              "does not support it")
        # Name is only used for testing purposes
        self.first_check = threading.Thread(target=first_check)
        self.first_check.start()

    def stop(self) -> None:
        self.log.info("Stopping notifier")
        with self._lock:
            if not self._started:
                self.log.warning("Not stopping notifier: Already stopped")
                return

            # Stop a scheduled retry or check
            self.log.debug("Canceling pending checks")
            if self._timer is not None:
                self._timer.cancel()

            self.log.info("Notifier is starting teardown")
            try:
                self.teardown()
            except NotImplementedError:
                self.log.info("Notifier has no teardown")
                self._started = False
            else:
                self._started = False

    def do_notify(self) -> None:
        self.log.debug("On-demand notify waiting for lock")
        with self._lock:
            self.log.debug("Doing on-demand notify")
            if not self._started:
                self.log.error("Tried to do_notify when not started")
                raise NotStartedError(f"Notifier {self.name} cannot do_notify when "
                                      "not started")
            try:
                self.check()
            except NotImplementedError:
                self.log.info("Notifier does not support on-demand notifications")

    @abstractmethod
    def setup(self) -> None:
        """Do any setup and start ongoing IP address notifications. Setup
        should be complete before this function returns (e.g. opening socket
        connections, etc.) but ongoing notifications should continue in the
        background, e.g. on a separate thread.

        **Should be overridden by subclasses if required.**

        :raises NotifierSetupError: when there is a nonrecoverable error
                                    preventing notifier startup.
        """
        raise NotImplementedError

    @abstractmethod
    def teardown(self) -> None:
        """Halt ongoing IP address notifications, do any teardown, and stop any
        non-daemon threads so Python may exit.

        **Should be overridden by subclasses if required.**

        When this is called, there will be no pending invocations of
        :meth:`check_once`, and it's guaranteed that :meth:`setup` is complete.
        Apart from that, it is up to the implementation to ensure that
        inconvenient timing won't break any operations happening in background
        threads (e.g. that were started by :meth:`setup`).

        This must not raise any exceptions (other than
        :exc:`NotImplementedError` if not implemented).
        """
        raise NotImplementedError

    def check(self):
        """Check the current IP address and do a notify, retrying on failure.
        If the ``success_interval`` is nonzero (see
        :meth:`set_check_intervals`) and the check was successful, also
        schedule the next check.

        This is called automatically after notifier startup and for on-demand
        notifies. The notifier can also call this itself to trigger additional
        notifies. For example, the ``systemd`` notifier does this when it
        receives a DBus event saying the network status has changed.

        :raises NotImplementedError: if not supported by this notifier
        """
        self.log.debug("Check waiting for lock")
        with self._lock:
            if not self._started:
                self.log.info("Skipping check when notifier not running")
                return

            self._seq += 1
            self._retries = 0
            self.log.debug("(check seq: %d)", self._seq)
            self._check_and_schedule(self._seq)

    def _scheduled_check(self, seq: int):
        """Do a scheduled check (retry or poll), verifying that no new check
        has happened meanwhile"""
        with self._lock:
            if not self._started:
                # Notifier stopped before we could lock. Abort.
                self.log.debug("(invocation for seq %d aborted due to notifier"
                               " stopping)", seq)
            elif self._seq != seq:
                # Another update has happened in the time since this retry was
                # scheduled. Abort.
                self.log.debug("(invocation for seq %d aborted due to new "
                               "check)", seq)
            else:
                self.log.debug("(new invocation for check seq: %d)", seq)
                self._check_and_schedule(seq)

    def _check_and_schedule(self, seq: int):
        """Do a check, scheduling the next one if necessary after. Do not call
        without holding the lock."""
        try:
            self.check_once()
        except NotifyError:
            # Minimum retry interval the first time, doubling each retry after
            retry_delay = self._retry_min_interval * (2 ** self._retries)
            if retry_delay > self._retry_max_interval:
                retry_delay = self._retry_max_interval
            self._retries += 1
            self.log.info("Check failed. Retrying in %d secs. (seq %d)",
                          retry_delay, seq)
            self._timer = threading.Timer(retry_delay, self._scheduled_check,
                                          args=(seq,))
            self._timer.start()
        else:
            if self._success_interval <= 0:
                self.log.debug("(success, seq %d complete), seq")
                return
            self._retries = 0
            self.log.debug("(success for seq %d, next invocation in %d secs)",
                           seq, self._success_interval)
            self._timer = threading.Timer(self._success_interval,
                                          self._scheduled_check, args=(seq,))
            self._timer.start()

    @abstractmethod
    def check_once(self) -> None:
        """Check the current IP address and do a notify, if possible.

        **Should be overridden by subclasses if supported.**

        Some notifiers do not support notifying on demand (for example, they
        get the current address from an event, thus they can only notify when
        such an event happens). For those updaters, this method should raise
        :exc:`NotImplementedError` when called (which is the default behavior
        when not overridden).

        For any notifier that does support obtaining the current IP address on
        demand, this function should do that immediately and notify using
        :meth:`notify_ipv4` and :meth:`notify_ipv6`. Some additional
        guidelines:

        - Ruddr may not need both IPv4 and IPv6 addresses from this notifier.
          Call :meth:`want_ipv4` and :meth:`want_ipv6` to determine if either
          should be skipped.

        - Even if Ruddr wants an address type, it may or may not be an error if
          it cannot be provided. If :meth:`need_ipv4` returns ``True`` and an
          IPv4 address cannot be obtained, raise :exc:`NotifyError` (after
          notifying for the other address type, if necessary). The same goes
          for :meth:`need_ipv6` and availability of an IPv6 prefix.

        This is called at notifier startup, for on-demand notifies, and any
        time the notifier calls :meth:`check` itself.

        :raises NotifyError: if checking the current IP address failed (will
                             trigger a retry after a delay)
        :raises NotImplementedError: if not supported by this notifier
        """
        raise NotImplementedError
