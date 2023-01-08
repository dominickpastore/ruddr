import pytest
import ipaddress
import time

import doubles

import ruddr


# TODO notifier has been rewritten, update tests


@pytest.fixture
def notifier_factory():
    """Fixture creating a factory for fake :class:`~ruddr.Notifier`"""
    class NotifierFactory:
        def __init__(self):
            self._count = 0

        def __call__(self, **kwargs):
            self._count += 1
            config = kwargs
            return doubles.FakeNotifier(f'fake_notifier_{self._count}', config)
    return NotifierFactory()


@pytest.fixture
def updater_factory():
    """Fixture creating a factory for mock :class:`~ruddr.Updater`"""
    class UpdaterFactory:
        def __init__(self):
            self._count = 0

        def __call__(self, **kwargs):
            self._count += 1
            config = kwargs
            return doubles.MockUpdater(f'mock_updater_{self._count}', config)
    return UpdaterFactory()


@pytest.fixture
def mock_updater(updater_factory):
    """Fixture creating a mock :class:`~ruddr.Updater` that keeps a list of
    IP addresses it receives"""
    return updater_factory()


def test_ipv4_ready_false(notifier_factory, mock_updater):
    """Test attaching updaters with ipv4_ready set to false is error"""
    fake_notifier = notifier_factory(ipv4_ready='false')

    # Expect no exception for IPv6
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    with pytest.raises(ruddr.ConfigError):
        fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)


def test_ipv6_ready_false(notifier_factory, mock_updater):
    """Test attaching updaters with ipv6_ready set to false is error"""
    fake_notifier = notifier_factory(ipv6_ready='false')

    # Expect no exception for IPv4
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    with pytest.raises(ruddr.ConfigError):
        fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)


def test_ipv4_ready_false_not_attached(notifier_factory, mock_updater):
    """Test attaching only IPv6 updater with ipv4_ready set to false"""
    fake_notifier = notifier_factory(ipv4_ready='false')
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))
    # Well-written notifiers don't call notify_ipv4() when want_ipv4() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv6Network('5678::/64'),
    ]


def test_ipv6_ready_false_not_attached(notifier_factory, mock_updater):
    """Test attaching only IPv4 updater with ipv6_ready set to false"""
    fake_notifier = notifier_factory(ipv6_ready='false')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv6)
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    # Well-written notifiers don't call notify_ipv6() when want_ipv6() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
    ]


def test_skip_ipv4_attach_ipv4(notifier_factory, mock_updater):
    """Test attaching an updater for IPv4 when IPv4 is skipped does nothing"""
    fake_notifier = notifier_factory(skip_ipv4='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    assert not fake_notifier.want_ipv4()


def test_skip_ipv4_attach_both(notifier_factory, mock_updater):
    """Test attaching an updater when IPv4 is skipped works for IPv6"""
    fake_notifier = notifier_factory(skip_ipv4='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))
    # Well-written notifiers don't call notify_ipv4() when want_ipv4() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv6Network('5678::/64'),
    ]


def test_skip_ipv6_attach_ipv6(notifier_factory, mock_updater):
    """Test attaching an updater for IPv6 when IPv6 is skipped does nothing"""
    fake_notifier = notifier_factory(skip_ipv6='true')
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    assert not fake_notifier.want_ipv6()


def test_skip_ipv6_attach_both(notifier_factory, mock_updater):
    """Test attaching an updater when IPv6 is skipped works for IPv4"""
    fake_notifier = notifier_factory(skip_ipv6='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    # Well-written notifiers don't call notify_ipv6() when want_ipv6() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
    ]


def test_ipv4_ready_false_and_skipped(notifier_factory, mock_updater):
    """Test attaching updater with ipv4_ready set to false but IPv4 skipped
    does not raise error"""
    fake_notifier = notifier_factory(skip_ipv4='true', ipv4_ready='false')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))
    # Well-written notifiers don't call notify_ipv4() when want_ipv4() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv6Network('5678::/64'),
    ]


def test_ipv6_ready_false_and_skipped(notifier_factory, mock_updater):
    """Test attaching updater with ipv6_ready set to false but IPv6 skipped
    does not raise error"""
    fake_notifier = notifier_factory(skip_ipv6='true', ipv6_ready='false')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    # Well-written notifiers don't call notify_ipv6() when want_ipv6() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
    ]


def test_skip_both_error(notifier_factory):
    """Test that setting both skip_ipv4 and skip_ipv6 causes an exception"""
    with pytest.raises(ruddr.ConfigError):
        notifier_factory(skip_ipv4='true', skip_ipv6='true')


def test_multiple_updaters(notifier_factory, updater_factory):
    """Test multiple updaters attached to a single notifier"""
    fake_notifier = notifier_factory()
    mock_updater_1 = updater_factory()
    mock_updater_2 = updater_factory()
    fake_notifier.attach_ipv4_updater(mock_updater_1.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater_1.update_ipv6)
    fake_notifier.attach_ipv4_updater(mock_updater_2.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater_2.update_ipv6)

    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert mock_updater_1.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
        ipaddress.IPv6Network('5678::/64'),
    ]

    assert mock_updater_2.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
        ipaddress.IPv6Network('5678::/64'),
    ]


def test_schedulednotifier_one_retry():
    """Test ScheduledNotifier retries after failed notify, then not again until
    success interval after a successful notify"""
    notifier = doubles.MockScheduledNotifier(
        'mock_notifier',
        7, 1, 5,
        (False, True, True)
    )
    notifier.start()
    expected = (1, 7)
    time.sleep(sum(expected) + 0.5)
    notifier.stop()
    assert all(-0.5 < a - e < 0.5 for a, e in zip(notifier.intervals, expected))


def test_schedulednotifier_two_retry():
    """Test ScheduledNotifier retries after failed notify, then after a longer
    delay after a second failed notify, then not again until the success
    interval after a successful notify"""
    notifier = doubles.MockScheduledNotifier(
        'mock_notifier',
        7, 1, 5,
        (False, False, True, True)
    )
    notifier.start()
    expected = (1, 2, 7)
    time.sleep(sum(expected) + 0.5)
    notifier.stop()
    assert all(-0.5 < a - e < 0.5 for a, e in zip(notifier.intervals, expected))


def test_schedulednotifier_many_retry():
    """Test ScheduledNotifier retries after failed notify, continues retrying
    after successively longer delays after repeated failures, then not again
    until the success interval after a successful notify"""
    notifier = doubles.MockScheduledNotifier(
        'mock_notifier',
        7, 1, 5,
        (False, False, False, False, False, True, True)
    )
    notifier.start()
    expected = (1, 2, 4, 5, 5, 7)
    time.sleep(sum(expected) + 0.5)
    notifier.stop()
    assert all(-0.5 < a - e < 0.5 for a, e in zip(notifier.intervals, expected))


def test_schedulednotifier_fail_and_manual_success():
    """Test ScheduledNotifier does not check again until the success interval
    after a failed notify and an immediate successful manual notify"""
    notifier = doubles.MockScheduledNotifier(
        'mock_notifier',
        7, 1, 5,
        (False, True, True)
    )
    notifier.start()
    notifier.check()
    expected = (0, 7)
    time.sleep(sum(expected) + 0.5)
    notifier.stop()
    assert all(-0.5 < a - e < 0.5 for a, e in zip(notifier.intervals, expected))


def test_schedulednotifier_two_fail_and_manual_fail():
    """Test ScheduledNotifier retries after a failed notify, retries after a
    longer delay after a second failed notify, then retries after a short
    delay after a failed manual notify, then not again until the success
    interval after a successful notify"""
    notifier = doubles.MockScheduledNotifier(
        'mock_notifier',
        7, 1, 5,
        (False, False, False, False, True, True)
    )
    notifier.start()
    expected1 = (1, 2, 0.5)
    time.sleep(sum(expected1))
    notifier.check()
    expected2 = (1, 7)
    time.sleep(sum(expected2) + 0.5)
    notifier.stop()
    expected = expected1 + expected2
    assert all(-0.5 < a - e < 0.5 for a, e in zip(notifier.intervals, expected))


def test_schedulednotifier_success():
    """Test ScheduledNotifier repeats successful notify after success
    interval"""
    notifier = doubles.MockScheduledNotifier(
        'mock_notifier',
        7, 1, 5,
        (True, True, True)
    )
    notifier.start()
    expected = (7, 7)
    time.sleep(sum(expected) + 0.5)
    notifier.stop()
    assert all(-0.5 < a - e < 0.5 for a, e in zip(notifier.intervals, expected))


def test_schedulednotifier_stop():
    """Test ScheduledNotifier stops checking after stopped"""
    notifier = doubles.MockScheduledNotifier(
        'mock_notifier',
        7, 1, 5,
        (True, True, True)
    )
    notifier.start()
    expected = (7,)
    time.sleep(sum(expected) + 0.5)
    notifier.stop()
    time.sleep(7)
    assert len(notifier.timestamps) == 2
    assert all(-0.5 < a - e < 0.5 for a, e in zip(notifier.intervals, expected))
