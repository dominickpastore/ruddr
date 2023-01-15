"""Test doubles for use in test classes and fixtures"""
import itertools

import ruddr


class MockBaseUpdater(ruddr.BaseUpdater):
    """Simple mock updater that keeps a list of IP updates it receives"""

    def __init__(self, name):
        super().__init__(name, None)
        self.published_addresses = []

    def initial_update(self):
        pass

    def update_ipv4(self, address):
        self.published_addresses.append(address)

    def update_ipv6(self, network):
        self.published_addresses.append(network)


class FakeNotifier(ruddr.BaseNotifier):
    """A simple notifier that notifies on demand. Extends BaseNotifier."""
    # Note: Tests can trigger notifying by calling .notify_ipv4() and
    # .notify_ipv6() directly

    def __init__(self, name, config):
        super().__init__(name, config)
        # Config vars to test .ipv4_ready() and .ipv6_ready()
        self._ipv4_ready = (config.get('ipv4_ready', 'true').lower() in
                            ('true', 'yes', 'on', '1'))
        self._ipv6_ready = (config.get('ipv6_ready', 'true').lower() in
                            ('true', 'yes', 'on', '1'))

    def ipv4_ready(self):
        return self._ipv4_ready

    def ipv6_ready(self):
        return self._ipv6_ready


class MockNotifier(ruddr.Notifier):
    """A mock scheduled notifier that keeps track of when checks are scheduled
    and retried"""

    def __init__(self, name, config, success_sequence=None,
                 setup_implemented=True, teardown_implemented=True,
                 check_implemented=True):
        super().__init__(name, config)

        #: The order of successes and fails for check_once
        if success_sequence is None:
            self.success_iter = itertools.repeat(True)
        else:
            self.success_iter = iter(success_sequence)

        self.setup_implemented = setup_implemented
        self.teardown_implemented = teardown_implemented
        self.check_implemented = check_implemented

        #: The order the abstract methods were called
        self.call_sequence = []

    @property
    def setup_count(self):
        return sum(call == 'setup' for call in self.call_sequence)

    @property
    def teardown_count(self):
        return sum(call == 'teardown' for call in self.call_sequence)

    @property
    def check_count(self):
        return sum(call == 'check' for call in self.call_sequence)

    def setup(self):
        self.call_sequence.append('setup')
        if not self.setup_implemented:
            raise NotImplementedError

    def teardown(self):
        self.call_sequence.append('teardown')
        if not self.teardown_implemented:
            raise NotImplementedError

    def check_once(self):
        self.call_sequence.append('check')
        if not self.check_implemented:
            raise NotImplementedError
        success = next(self.success_iter)
        if not success:
            raise ruddr.NotifyError

    def join_first_check(self):
        """Wait for first check after :meth:`start` to finish"""
        self.first_check.join()
