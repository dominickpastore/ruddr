"""Test doubles for use in test classes and fixtures"""
import collections
import errno
import ipaddress
import itertools
from typing import List, Tuple, Set, Optional, Dict

import ruddr
from ruddr import NotifierSetupError, Addrfile, PublishError


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


class MockUpdater(ruddr.Updater):
    """Mock Updater that tracks calls to its abstract functions"""

    def __init__(self, name: str, addrfile: Addrfile,
                 ipv4_errors=None, ipv6_errors=None,
                 ipv4_implemented=True, ipv6_implemented=True):
        super().__init__(name, addrfile)
        self.ipv4s_published: List[ipaddress.IPv4Address] = []
        self.ipv6s_published: List[ipaddress.IPv6Network] = []

        if ipv4_errors is None:
            self.ipv4_iter = itertools.repeat(None)
        else:
            self.ipv4_iter = iter(ipv4_errors)
        if ipv6_errors is None:
            self.ipv6_iter = itertools.repeat(None)
        else:
            self.ipv6_iter = iter(ipv6_errors)

        self.ipv4_implemented = ipv4_implemented
        self.ipv6_implemented = ipv6_implemented

    def publish_ipv4(self, address: ipaddress.IPv4Address):
        self.ipv4s_published.append(address)
        if not self.ipv4_implemented:
            raise NotImplementedError
        error = next(self.ipv4_iter)
        if error is not None:
            raise error

    def publish_ipv6(self, network: ipaddress.IPv6Network):
        self.ipv6s_published.append(network)
        if not self.ipv6_implemented:
            raise NotImplementedError
        error = next(self.ipv6_iter)
        if error is not None:
            raise error


class MockOneWayUpdater(ruddr.OneWayUpdater):
    """Mock OneWayUpdater that tracks calls to its abstract functions"""

    def __init__(self, name: str, addrfile: Addrfile,
                 ipv4_implemented=True, ipv6_implemented=True,
                 ipv4_errors=None, ipv6_errors=None):
        super().__init__(name, addrfile)
        self.ipv4s_published: collections.Counter[
            Tuple[str, ipaddress.IPv4Address]
        ] = collections.Counter()
        self.ipv6s_published: collections.Counter[
            Tuple[str, ipaddress.IPv6Address]
        ] = collections.Counter()

        self.ipv4_implemented = ipv4_implemented
        self.ipv6_implemented = ipv6_implemented

        # Sets of hostnames which should raise PublishError when published
        self.ipv4_errors: Set[str] = set()
        if ipv4_errors is not None:
            for host in ipv4_errors:
                self.ipv4_errors.add(host)
        self.ipv6_errors: Set[str] = set()
        if ipv6_errors is not None:
            for host in ipv6_errors:
                self.ipv6_errors.add(host)

    def publish_ipv4_one_host(self,
                              hostname: str,
                              address: ipaddress.IPv4Address):
        self.ipv4s_published[(hostname, address)] += 1
        if not self.ipv4_implemented:
            raise NotImplementedError
        if hostname in self.ipv4_errors:
            raise PublishError

    def publish_ipv6_one_host(self,
                              hostname: str,
                              address: ipaddress.IPv6Address):
        self.ipv6s_published[(hostname, address)] += 1
        if not self.ipv6_implemented:
            raise NotImplementedError
        if hostname in self.ipv6_errors:
            raise PublishError


class MockTwoWayZoneUpdater(ruddr.TwoWayZoneUpdater):
    """Mock TwoWayZoneUpdater that tracks calls to its abstract methods"""

    def __init__(self, name: str, addrfile: Addrfile, datadir,
                 get_zones_result=None,
                 fetch_zone_ipv4s_result=None,
                 fetch_zone_ipv6s_result=None,
                 fetch_subdomain_ipv4s_result=None,
                 fetch_subdomain_ipv6s_result=None,
                 put_zone_ipv4s_result=None,
                 put_zone_ipv6s_result=None,
                 put_subdomain_ipv4_result=None,
                 put_subdomain_ipv6s_result=None):
        super().__init__(name, addrfile, str(datadir))

        self.get_zones_result = get_zones_result
        self.fetch_zone_ipv4s_result = fetch_zone_ipv4s_result
        self.fetch_zone_ipv6s_result = fetch_zone_ipv6s_result
        self.fetch_subdomain_ipv4s_result = fetch_subdomain_ipv4s_result
        self.fetch_subdomain_ipv6s_result = fetch_subdomain_ipv6s_result
        self.put_zone_ipv4s_result = put_zone_ipv4s_result
        self.put_zone_ipv6s_result = put_zone_ipv6s_result
        self.put_subdomain_ipv4_result = put_subdomain_ipv4_result
        self.put_subdomain_ipv6s_result = put_subdomain_ipv6s_result

        self.get_zones_call_count = 0
        self.fetch_zone_ipv4s_calls = []
        self.fetch_zone_ipv6s_calls = []
        self.fetch_subdomain_ipv4s_calls = []
        self.fetch_subdomain_ipv6s_calls = []
        self.put_zone_ipv4s_calls = []
        self.put_zone_ipv6s_calls = []
        self.put_subdomain_ipv4_calls = []
        self.put_subdomain_ipv6s_calls = []

    def get_zones(self) -> List[str]:
        self.get_zones_call_count += 1
        if self.get_zones_result is None:
            raise NotImplementedError
        return self.get_zones_result

    def fetch_zone_ipv4s(
        self, zone: str
    ) -> List[Tuple[str, ipaddress.IPv4Address, Optional[int]]]:
        self.fetch_zone_ipv4s_calls.append(zone)
        if self.fetch_zone_ipv4s_result is None:
            raise NotImplementedError
        result = self.fetch_zone_ipv4s_result[zone]
        if isinstance(result, Exception):
            raise result
        return result

    def fetch_zone_ipv6s(
        self, zone: str
    ) -> List[Tuple[str, ipaddress.IPv6Address, Optional[int]]]:
        self.fetch_zone_ipv6s_calls.append(zone)
        if self.fetch_zone_ipv6s_result is None:
            raise NotImplementedError
        result = self.fetch_zone_ipv6s_result[zone]
        if isinstance(result, Exception):
            raise result
        return result

    def fetch_subdomain_ipv4s(
        self, subdomain: str, zone: str
    ) -> List[Tuple[ipaddress.IPv4Address, Optional[int]]]:
        self.fetch_subdomain_ipv4s_calls.append((subdomain, zone))
        if self.fetch_subdomain_ipv4s_result is None:
            raise NotImplementedError
        result = self.fetch_subdomain_ipv4s_result[(subdomain, zone)]
        if isinstance(result, Exception):
            raise result
        return result

    def fetch_subdomain_ipv6s(
        self, subdomain: str, zone: str
    ) -> List[Tuple[ipaddress.IPv6Address, Optional[int]]]:
        self.fetch_subdomain_ipv6s_calls.append((subdomain, zone))
        if self.fetch_subdomain_ipv6s_result is None:
            raise NotImplementedError
        result = self.fetch_subdomain_ipv6s_result[(subdomain, zone)]
        if isinstance(result, Exception):
            raise result
        return result

    def put_zone_ipv4s(
        self,
        zone: str,
        records: Dict[str, Tuple[List[ipaddress.IPv4Address], Optional[int]]]
    ):
        self.put_zone_ipv4s_calls.append((zone, records))
        if self.put_zone_ipv4s_result is None:
            raise NotImplementedError
        result = self.put_zone_ipv4s_result[zone]
        if isinstance(result, Exception):
            raise result
        return result

    def put_zone_ipv6s(
        self,
        zone: str,
        records: Dict[str, Tuple[List[ipaddress.IPv6Address], Optional[int]]]
    ):
        self.put_zone_ipv6s_calls.append((zone, records))
        if self.put_zone_ipv6s_result is None:
            raise NotImplementedError
        result = self.put_zone_ipv6s_result[zone]
        if isinstance(result, Exception):
            raise result
        return result

    def put_subdomain_ipv4(self, subdomain: str, zone: str,
                           address: ipaddress.IPv4Address, ttl: Optional[int]):
        self.put_subdomain_ipv4_calls.append((subdomain, zone, address, ttl))
        if self.put_subdomain_ipv4_result is None:
            raise NotImplementedError
        result = self.put_subdomain_ipv4_result[(subdomain, zone)]
        if isinstance(result, Exception):
            raise result
        return result

    def put_subdomain_ipv6s(self, subdomain: str, zone: str,
                            addresses: List[ipaddress.IPv6Address],
                            ttl: Optional[int]):
        self.put_subdomain_ipv6s_calls.append((subdomain, zone,
                                               addresses, ttl))
        if self.put_subdomain_ipv6s_result is None:
            raise NotImplementedError
        result = self.put_subdomain_ipv6s_result[(subdomain, zone)]
        if isinstance(result, Exception):
            raise result
        return result
