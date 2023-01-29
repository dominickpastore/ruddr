"""Test doubles for use in test classes and fixtures"""
import errno
import itertools

import ruddr
from ruddr import NotifierSetupError


class BrokenFile:
    """File-like object that raises an exception when being read from"""
    def __init__(self, write_broken=False):
        self.write_broken = write_broken

    def __iter__(self):
        if self.write_broken:
            return iter([])
        else:
            raise OSError(errno.ETIMEDOUT, "timeout")

    def read(self, *_):
        if self.write_broken:
            return ""
        else:
            raise OSError(errno.ETIMEDOUT, "timeout")

    def write(self, *_):
        if self.write_broken:
            raise OSError(errno.ETIMEDOUT, "timeout")
        else:
            return 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockBaseUpdater(ruddr.BaseUpdater):
    """Simple mock updater that keeps a list of IP updates it receives"""

    def __init__(self, name, addrfile=None, config=None, err_sequence=None):
        super().__init__(name, addrfile)
        self.config = config
        self.published_addresses = []

        #: The order of successes and fails for retry_test. None means success,
        #: an error means raise that error
        if err_sequence is None:
            self.err_iter = itertools.repeat(None)
        else:
            self.err_iter = iter(err_sequence)
        #: The list of calls to retry_test
        self.retry_sequence = []

    @ruddr.updaters.updater.Retry
    def retry_test(self, param: int):
        """A dummy function to test @Retry. Only used in test_baseupdater."""
        self.retry_sequence.append(param)
        error = next(self.err_iter)
        if error is not None:
            raise error

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
        self.config = config
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
    """A mock Notifier whose checks succeed and fail in a predetermined order
    and which tracks when calls were made"""

    def __init__(self, name, config, success_sequence=None,
                 setup_implemented=True, teardown_implemented=True,
                 check_implemented=True, setup_error=False):
        super().__init__(name, config)

        #: The order of successes and fails for check_once
        if success_sequence is None:
            self.success_iter = itertools.repeat(True)
        else:
            self.success_iter = iter(success_sequence)

        self.setup_implemented = setup_implemented
        self.teardown_implemented = teardown_implemented
        self.check_implemented = check_implemented
        self.setup_error = setup_error

        #: The order the abstract methods were called
        self.call_sequence = []

        # Used only for test_manager.py
        self.stop_count = 0

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
        if self.setup_error:
            raise NotifierSetupError

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

    # test_manager needs to tell if stop was called even if start was not
    def stop(self) -> None:
        self.stop_count += 1
        super().stop()

    def join_first_check(self):
        """Wait for first check after :meth:`start` to finish"""
        self.first_check.join()
