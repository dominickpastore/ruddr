"""Base class for Ruddr notifiers"""

import functools
import logging
import threading
import types

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
                                   in ('true', 'on', '1'))
        except ValueError:
            self.log.critical("'skip_ipv4' must be boolean (true/yes/1/"
                              "false/no/0)")
            raise ConfigError(f"'skip_ipv4' option for {self.name} must"
                              "be boolean (true/yes/1/false/no/0)")
        try:
            self._skip_ipv6 = (config.get('skip_ipv6', 'false').lower()
                                   in ('true', 'on', '1'))
        except ValueError:
            self.log.critical("'skip_ipv6' must be boolean (true/yes/1/"
                              "false/no/0)")
            raise ConfigError(f"'skip_ipv6' option for {self.name} must"
                              "be boolean (true/yes/1/false/no/0)")

        try:
            self._ipv4_required = (config.get('ipv4_required', 'true').lower()
                                   in ('true', 'on', '1'))
        except ValueError:
            self.log.critical("'ipv4_required' must be boolean (true/yes/1/"
                              "false/no/0)")
            raise ConfigError(f"'ipv4_required' option for {self.name} must"
                              "be boolean (true/yes/1/false/no/0)")
        try:
            self._ipv6_required = (config.get('ipv6_required', 'false').lower()
                                   in ('true', 'on', '1'))
        except ValueError:
            self.log.critical("'ipv6_required' must be boolean (true/yes/1/"
                              "false/no/0)")
            raise ConfigError(f"'ipv6_required' option for {self.name} must"
                              "be boolean (true/yes/1/false/no/0)")

        self.ipv4_updaters = []
        self.ipv6_updaters = []

    def attach_ipv4_updater(self, updater):
        """Attach an IPv4 update function to this notifier. Generally called
        by an updater to provide its update function to the notifier.

        :param updater: A callable that accepts an :class:`IPv4Address` to be
                        called whenever the IPv4 address might have been
                        updated. It is the callee's responsibility to ensure
                        the update eventually happens successfully (e.g. by
                        scheduling a retry in a separate thread if it fails),
                        but this function should not block longer than a single
                        update attempt.
        """
        self.log.debug("Attaching %s (IPv4) to notifier %s",
                       updater.__name__, self.name)
        if len(self.ipv4_updaters) == 0 and not self.ipv4_ready():
            self.log.critical("Cannot use as IPv4 notifier without required "
                              "IPv4 config")
            raise ConfigError("Notifier %s cannot be an IPv4 notifier without "
                              "required IPv4 config" % self.name)
        self.ipv4_updaters.append(updater)

    def attach_ipv6_updater(self, updater):
        """Attach an IPv6 update function to this notifier. Generally called
        by an updater to provide its update function to the notifier.

        :param updater: A callable that accepts an :class:`IPv6Network` to be
                        called whenever the IPv6 prefix might have been
                        updated. It is the callee's responsibility to ensure
                        the update eventually happens successfully (e.g. by
                        scheduling a retry in a separate thread if it fails),
                        but this function should not block longer than a single
                        update attempt.
        """
        self.log.debug("Attaching %s (IPv6) to notifier %s",
                       updater.__name__, self.name)
        if len(self.ipv6_updaters) == 0 and not self.ipv6_ready():
            self.log.critical("Cannot use as IPv6 notifier without required "
                              "IPv4 config")
            raise ConfigError("Notifier %s cannot be an IPv6 notifier without "
                              "required IPv6 config" % self.name)
        self.ipv6_updaters.append(updater)

    def notify_ipv4(self, address):
        """Subclasses must call this to notify all the attached IPv4 updaters of
        a (possibly) new IPv4 address.

        :param address: The (possibly) new :class:`IPv4Address`
        """
        self.log.debug("Notifier %s notifying attached updaters of IPv4 %s",
                       self.name, address.exploded)
        for updater in self.ipv4_updaters:
            updater(address)

    def notify_ipv6(self, address):
        """Subclasses must call this to notify all the attached IPv6 updaters
        of a (possibly) new IPv6 prefix.

        :param address: The :class:`IPv6Network` representing the (possibly)
                        new prefix
        """
        self.log.debug("Notifier %s notifying attached updaters of IPv6 %s",
                       self.name, address.compressed)
        for updater in self.ipv6_updaters:
            updater(address)

    def want_ipv4(self):
        """Subclasses should call this to determine whether to check for
        current IPv4 addresses at all.

        :return: True or False
        """
        return (not self._skip_ipv4) and len(self.ipv4_updaters) > 0

    def want_ipv6(self):
        """Subclasses should call this to determine whether to check for
        current IPv6 addresses at all.

        :return: True or False
        """
        return (not self._skip_ipv6) and len(self.ipv6_updaters) > 0

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


class Scheduled:
    """Use as a decorator ``@Scheduled`` to make a method of a
    :class:`~ruddr.ScheduledNotifier` into a scheduled method.
    """

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.seq = 0
        self.fail_interval = None
        self.lock = threading.RLock()

    # Emulate binding behavior in normal functions that become methods.
    # See https://docs.python.org/3/howto/descriptor.html#functions-and-methods
    # (Without this, the 'self' argument is not passed through)
    def __get__(self, obj, obj_cls=None):
        if obj is None:
            # This check should not be necessary in this case...it only
            # evaluates to True when calling a decorated method that's not
            # @staticmethod and not @classmethod using the class name
            # (e.g. Class.my_func()). But it's here just in case.
            return self
        return types.MethodType(self, obj)

    def __call__(self, obj, *args, **kwargs):
        with self.lock:
            self.seq += 1
            self.fail_interval = None
            obj.log.debug("(Schedule seq: %d)", self.seq)
            self._wrapper(self.seq, obj, *args, **kwargs)

    def _run_scheduled(self, seq, obj, *args, **kwargs):
        """Do a scheduled invocation of the function. If any run has happened
        in the meantime (identified by the current sequence number being
        greater than ours), abort."""
        with self.lock:
            if self.seq > seq:
                obj.log.debug("(Invocation for schedule seq %d aborted due to "
                              "new invocation in the meantime.", seq)
            else:
                obj.log.debug("(Next invocation for schedule seq: %d)", seq)
                self._wrapper(seq, obj, *args, **kwargs)

    def _wrapper(self, seq, obj, *args, **kwargs):
        """Run the function and schedule its next invocation"""
        try:
            self.func(obj, *args, **kwargs)
        except NotifyError:
            if self.fail_interval is None:
                self.fail_interval = obj.fail_min_interval
            else:
                self.fail_interval *= 2
                if self.fail_interval > obj.fail_max_interval:
                    self.fail_interval = obj.fail_max_interval
            obj.log.info("(Failed. Will retry in %d seconds.)",
                         seq, self.fail_interval)
            retry_delay = self.fail_interval
        else:
            self.fail_interval = None
            retry_delay = obj.success_interval
            obj.log.debug("(Invocation success for schedule seq: %d)", seq)

        if retry_delay > 0:
            timer = threading.Timer(retry_delay, self._run_scheduled,
                                    args=(seq, obj, *args), kwargs=kwargs)
            timer.daemon = True
            timer.start()


class SchedulerNotifier(Notifier):
    """An abstract notifier with the ability to schedule checks (or other
    tasks) to happen on regular intervals and retry when failed.

    Decorating a function with the ``@Scheduled`` decorator makes it
    a scheduled function.

    Instance attributes :attr:`success_interval`, :attr:`fail_min_interval`,
    and :attr:`fail_max_interval` can be modified by subclasses to control the
    timing.

    Whenever a scheduled function is invoked, whether explicitly or by prior
    scheduling, the timer for the next scheduled invocation is reset according
    to the configured intervals and whether it was successful.

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
