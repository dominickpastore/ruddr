"""Test doubles for use in test classes and fixtures"""

import time

from ruddr import Updater, BaseNotifier, Notifier, NotifyError


class MockUpdater(Updater):
    """Simple mock updater that keeps a list of IP updates it receives"""

    def __init__(self, name, config):
        super().__init__(name, config)
        self.published_addresses = []

    def publish_ipv4(self, address):
        self.published_addresses.append(address)

    def publish_ipv6(self, network):
        self.published_addresses.append(network)


class FakeNotifier(BaseNotifier):
    """A simple notifier that notifies on demand. Extends BaseNotifier."""
    # Note: Tests can trigger notifying by calling .notify_ipv4() and
    # .notify_ipv6() directly

    def __init__(self, name, config):
        super().__init__(name, config)
        # Config vars to test .ipv4_ready() and .ipv6_ready()
        self._ipv4_ready = (config.get('ipv4_ready', 'true').lower() in
                            ('true', 'yes', 'on', '1'))
        self._ipv6_ready = (config.get('ipv4_ready', 'true').lower() in
                            ('true', 'yes', 'on', '1'))

    def ipv4_ready(self):
        return self._ipv4_ready

    def ipv6_ready(self):
        return self._ipv6_ready


# TODO This should inherit from regular Notifier now
class MockScheduledNotifier(ScheduledNotifier):
    """A mock scheduled notifier that keeps track of when checks are scheduled
    and retried"""

    def __init__(self, name, success_interval, fail_min_interval,
                 fail_max_interval, success_sequence):
        super().__init__(name, dict())

        self.success_interval = success_interval
        self.fail_min_interval = fail_min_interval
        self.fail_max_interval = fail_max_interval

        self.success_sequence = list(success_sequence)

        #: Keeps a list of timestamps for when each check happened
        self.timestamps = []

    @property
    def intervals(self):
        return [y - x for x, y in zip(self.timestamps, self.timestamps[1:])]

    def check_once(self):
        self.timestamps.append(time.monotonic())
        success = self.success_sequence.pop(0)
        if not success:
            raise NotifyError
