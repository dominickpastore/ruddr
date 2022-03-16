"""Base class for Ruddr notifiers"""

import logging
import threading

from ..exceptions import NotifyError, ConfigError


class Notifier:
    """Base class for Ruddr notifiers

    :param name: Name of the updater (from config section heading)
    :param config: Dict of config options for this updater
    """

    def __init__(self, name, config):
        #: Notifier name (from config section heading)
        self.name = name

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
            self._skip_ipv4 = (config.get('skip_ipv4', 'false').lower()
                               in ('true', 'on', 'yes', '1'))
        except ValueError:
            self.log.critical("'skip_ipv4' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'skip_ipv4' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")
        try:
            self._skip_ipv6 = (config.get('skip_ipv6', 'false').lower()
                               in ('true', 'on', 'yes', '1'))
        except ValueError:
            self.log.critical("'skip_ipv6' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'skip_ipv6' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")

        try:
            self._ipv4_required = (config.get('ipv4_required', 'true').lower()
                                   in ('true', 'on', 'yes', '1'))
        except ValueError:
            self.log.critical("'ipv4_required' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'ipv4_required' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")
        try:
            self._ipv6_required = (config.get('ipv6_required', 'false').lower()
                                   in ('true', 'on', 'yes', '1'))
        except ValueError:
            self.log.critical("'ipv6_required' must be boolean (true/yes/on/1/"
                              "false/no/off/0)")
            raise ConfigError(f"'ipv6_required' option for {self.name} must"
                              "be boolean (true/yes/on/1/false/no/off/0)")

        self._ipv4_update_funcs = []
        self._ipv6_update_funcs = []

    def attach_ipv4_updater(self, update_func):
        """Attach an IPv4 update function to this notifier. No effect if IPv4
        is skipped for this notifier.

        :param update_func: A callable that accepts an :class:`IPv4Address` to
                            be called whenever the IPv4 address might have been
                            updated. It is the callee's responsibility to
                            ensure the update eventually happens successfully
                            (e.g. by scheduling a retry in a separate thread if
                            it fails), but this function should not block
                            longer than a single update attempt.
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

    def attach_ipv6_updater(self, update_func):
        """Attach an IPv6 update function to this notifier. No effect if IPv6
        is skipped for this notifier.

        :param update_func: A callable that accepts an :class:`IPv6Network` to
                            be called whenever the IPv6 prefix might have been
                            updated. It is the callee's responsibility to
                            ensure the update eventually happens successfully
                            (e.g. by scheduling a retry in a separate thread if
                            it fails), but this function should not block
                            longer than a single update attempt.
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

    def notify_ipv4(self, address):
        """Subclasses must call this to notify all the attached IPv4 updaters of
        a (possibly) new IPv4 address.

        Subclasses should not call this if :meth:`want_ipv4` is false.

        :param address: The (possibly) new :class:`IPv4Address`
        """
        self.log.debug("Notifier %s notifying attached updaters of IPv4 %s",
                       self.name, address.exploded)
        for update_func in self._ipv4_update_funcs:
            update_func(address)

    def notify_ipv6(self, address):
        """Subclasses must call this to notify all the attached IPv6 updaters
        of a (possibly) new IPv6 prefix.

        Subclasses should not call this if :meth:`want_ipv6` is false.

        :param address: The :class:`IPv6Network` representing the (possibly)
                        new prefix
        """
        self.log.debug("Notifier %s notifying attached updaters of IPv6 %s",
                       self.name, address.compressed)
        for update_func in self._ipv6_update_funcs:
            update_func(address)

    def want_ipv4(self):
        """Subclasses should call this to determine whether to check for
        current IPv4 addresses at all.

        :return: True or False
        """
        # Will be true if no updaters are configured, or they weren't attached
        # because skip_ipv4
        return len(self._ipv4_update_funcs) > 0

    def want_ipv6(self):
        """Subclasses should call this to determine whether to check for
        current IPv6 addresses at all.

        :return: True or False
        """
        # Will be true if no updaters are configured, or they weren't attached
        # because skip_ipv6
        return len(self._ipv6_update_funcs) > 0

    def need_ipv4(self):
        """Subclasses should call this to determine if a lack of IPv4 addressing
        is an error.

        :return: True or False
        """
        return self.want_ipv4() and self._ipv4_required

    def need_ipv6(self):
        """Subclasses should call this to determine if a lack of IPv6 addressing
        is an error.

        :return: True or False
        """
        return self.want_ipv6() and self._ipv6_required

    def ipv4_ready(self):
        """Check if all configuration required for IPv4 checks is present.

        Subclasses should override if there is any configuration only required
        for IPv4.
        """
        return True

    def ipv6_ready(self):
        """Check if all configuration required for IPv6 checks is present.

        Subclasses should override if there is any configuration only required
        for IPv6.
        """
        return True

    def check_once(self):
        """Check the IP address a single time and notify immediately.

        :raises NotifyError: if the check fails.

        Must be overridden by subclasses."""

    def start(self):
        """Begin ongoing IP address notifications. Should do the first check
        immediately. Further checks should run in a separate thread or
        otherwise be asynchronous.

        Must be overridden by subclasses.

        :raises NotifierSetupError: when there is a nonrecoverable error
                                    preventing notifier startup. Causes
                                    Ruddr to exit gracefully with a failure
                                    status.
        """

    def stop(self):
        """Halt ongoing IP address notifications. Clean up gracefully and stop
        any non-daemon threads so Python may exit.

        This should not raise any exceptions, even if called before
        :meth:`start` or after :meth:`start` fails.

        Must be overridden by subclasses.
        """


class ScheduledNotifier(Notifier):
    """An abstract notifier that schedules checks to happen at regular
    intervals and retry when failed.

    Instance attributes :attr:`success_interval`, :attr:`fail_min_interval`,
    and :attr:`fail_max_interval` can be modified by subclasses to control the
    timing.

    Single checks can be done with :meth:`check_once`. But, after the notifier
    is started, extra checks can be done with :meth:`check`, which
    automatically handles scheduling the next check according to the
    success/failure intervals and whether the check succeeded.

    Constructor parameters match :class:`~ruddr.Notifier`.
    """

    def __init__(self, name, config):
        super().__init__(name, config)

        #: When a scheduled function runs successfully, the next invocation
        #: will be scheduled this many seconds later. If zero, invocations will
        #: only be rescheduled after failed invocations.
        self.success_interval = 86400

        #: When a scheduled function fails (by raising
        #: :exc:`~ruddr.NotifyError`), the next invocation will be scheduled
        #: using an exponential backoff strategy. This attribute sets the
        #: scheduling interval for the first failure.
        self.fail_min_interval = 300

        #: After the scheduled function fails the first time, subsequent
        #: failures will be scheduled using successively longer intervals,
        #: until reaching the maximum length determined by this attribute. Once
        #: the maximum interval is reached, it will remain constant until the
        #: next successful invocation.
        self.fail_max_interval = 86400

        # The following are used for scheduling checks
        self._seq = 0   # Increments every time check() is called
        self._timer = None
        self._fail_interval = None
        self._lock = threading.RLock()

    def check_once(self):
        """Check the IP address a single time and notify immediately.

        Must be overridden by subclasses.

        :raises NotifyError: if the check fails.

        This function can be called by the manager to do a single check, but
        in :class:`~ruddr.ScheduledNotifier`, this same function is called to
        perform each scheduled check (by default—override
        :meth:`check_scheduled` to change that).

        When called as part of a scheduled check, raising
        :class:`~ruddr.NotifyError` or not determines whether to schedule the
        next check using the success or failure interval."""

    def check_scheduled(self):
        """Do a scheduled IP address check. By default, this calls
        :meth:`check_once`, but it can be overridden if that is not suitable.

        Raising :class:`~ruddr.NotifyError` or not determines whether to
        schedule the next check using the success or failure interval.

        Note that if a subclass needs to do an extra check (for example, the
        :class:`~ruddr.notifiers.systemd.SystemdNotifier` when it gets a DBus
        message from systemd-networkd), it should call :meth:`check` instead.
        That will ensure the next call is scheduled properly, which would not
        happen just by calling this method directly.

        :raises NotifyError: if the check fails.
        """
        self.check_once()

    def _run_check_and_schedule(self, seq):
        """Do a scheduled invocation of :meth:`_check_and_schedule`. Meant to
        be used as the target of a :class:`~threading.Timer`."""
        with self._lock:
            if self._seq > seq:
                self.log.debug("(Invocation for schedule seq %d aborted due "
                               "to new invocation in the meantime.)", seq)
            else:
                self.log.debug("(Next invocation for schedule seq: %d)", seq)
                self._check_and_schedule(seq)

    def _check_and_schedule(self, seq):
        """Run :meth:`check_scheduled` and schedule its next invocation"""
        try:
            self.check_scheduled()
        except NotifyError:
            if self._fail_interval is None:
                self._fail_interval = self.fail_min_interval
            else:
                self._fail_interval *= 2
                if self._fail_interval > self.fail_max_interval:
                    self._fail_interval = self.fail_max_interval
            self.log.info("(Seq %d failed. Will retry in %d seconds.)",
                          seq, self._fail_interval)
            retry_delay = self._fail_interval
        else:
            self._fail_interval = None
            retry_delay = self.success_interval
            self.log.debug("(Invocation success for schedule seq: %d)", seq)

        if retry_delay > 0:
            timer = threading.Timer(retry_delay,
                                    self._run_check_and_schedule,
                                    args=(seq,))
            timer.daemon = True
            self._timer = timer
            timer.start()

    def check(self):
        """Check the IP address and schedule the next check according to
        whether the check was successful and the success/failure intervals.

        This is the method to call if a subclass needs to do an extra check
        (for example, the :class:`~ruddr.notifiers.systemd.SystemdNotifier`
        when it gets a DBus message from systemd-networkd). That will ensure
        the next check is scheduled properly.

        If the most recent checks failed, the failure interval resets back to
        the minimum whenever this is called.
        """
        with self._lock:
            # Must still use sequence numbers to prevent race conditions (e.g.:
            # check is called and enters critical section, then timer expires
            # before code below runs. Then, _run_check_and_schedule() will run
            # but block entering its own critical section. The code below will
            # then continue, but it's too late to cancel the timer since it
            # already expired.)
            if self._timer is not None:
                self._timer.cancel()
            self._seq += 1
            self.log.debug("(Schedule seq: %d)", self._seq)
            self._fail_interval = None
            self._check_and_schedule(self._seq)

    def start(self):
        self.log.info("Starting notifier")
        # Do the first check, which also schedules future checks
        self.check()

    def stop(self):
        self.log.info("Stopping notifier")
        self._timer.cancel()
