import pytest
import ipaddress

import mocks

import ruddr


@pytest.fixture
def mock_updater():
    """Fixture creating a mock :class:`~ruddr.Updater` that keeps a list of
    IP addresses it receives"""
    updater_config = dict()
    return mocks.MockUpdater('mock_updater', updater_config)


def test_ipv4_ready_false(mock_updater):
    """Test attaching updaters with ipv4_ready set to false"""
    notifier_config = {
        # Defaults: no skip_ipv4, no skip_ipv6, ipv4_required, no ipv6_required
        'ipv4_ready': 'false',
    }
    mock_notifier = mocks.MockNotifier('mock_notifier', notifier_config)

    # Expect no exception for IPv6
    mock_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    with pytest.raises(ruddr.ConfigError):
        mock_notifier.attach_ipv4_updater(mock_updater.update_ipv4)


def test_ipv6_ready_false(mock_updater):
    """Test attaching updaters with ipv6_ready set to false"""
    notifier_config = {
        # Defaults: no skip_ipv4, no skip_ipv6, ipv4_required, no ipv6_required
        'ipv6_ready': 'false',
    }
    mock_notifier = mocks.MockNotifier('mock_notifier', notifier_config)

    # Expect no exception for IPv4
    mock_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    with pytest.raises(ruddr.ConfigError):
        mock_notifier.attach_ipv6_updater(mock_updater.update_ipv6)


def test_ipv4_ready_false_not_attached(mock_updater):
    """Test attaching only IPv6 updater with ipv4_ready set to false"""
    notifier_config = {
        # Defaults: no skip_ipv4, no skip_ipv6, ipv4_required, no ipv6_required
        'ipv4_ready': 'false',
    }
    mock_notifier = mocks.MockNotifier('mock_notifier', notifier_config)

    mock_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    mock_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    mock_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))
    # Well-written notifiers don't call notify_ipv4() when want_ipv4() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv6Network('5678::/64'),
    ]


def test_ipv6_ready_false_not_attached(mock_updater):
    """Test attaching only IPv4 updater with ipv6_ready set to false"""
    notifier_config = {
        # Defaults: no skip_ipv4, no skip_ipv6, ipv4_required, no ipv6_required
        'ipv6_ready': 'false',
    }
    mock_notifier = mocks.MockNotifier('mock_notifier', notifier_config)

    mock_notifier.attach_ipv4_updater(mock_updater.update_ipv6)
    mock_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    mock_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    # Well-written notifiers don't call notify_ipv6() when want_ipv6() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
    ]


def test_ipv4_ready_false_and_skipped(mock_updater):
    """Test attaching updater with ipv4_ready set to false but IPv4 skipped
    does not raise error"""
    notifier_config = {
        # Defaults: no skip_ipv6, ipv4_required, no ipv6_required
        'skip_ipv4': 'true',
        'ipv4_ready': 'false',
    }
    mock_notifier = mocks.MockNotifier('mock_notifier', notifier_config)

    mock_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    mock_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    mock_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    mock_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))
    # Well-written notifiers don't call notify_ipv4() when want_ipv4() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv6Network('5678::/64'),
    ]


def test_ipv6_ready_false_and_skipped(mock_updater):
    """Test attaching updater with ipv6_ready set to false but IPv6 skipped
    does not raise error"""
    notifier_config = {
        # Defaults: no skip_ipv4, ipv4_required, no ipv6_required
        'skip_ipv6': 'true',
        'ipv6_ready': 'false',
    }
    mock_notifier = mocks.MockNotifier('mock_notifier', notifier_config)

    mock_notifier.attach_ipv4_updater(mock_updater.update_ipv6)
    mock_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    mock_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    mock_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    # Well-written notifiers don't call notify_ipv6() when want_ipv6() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
    ]

# TODO test that notifier that's only attached to a skipped family is not
#  started (it should also raise a critical error, but that need not be tested)

# TODO test that ipv4 and ipv6 both set to skip causes error to be raised

# TODO test multiple updaters attached to a notifier

# TODO timed notifier retries after failed notify, then not again after
#  successful

# TODO timed notifier does not retry after failed notify and then immediate
#  manual successful notify

# TODO timed notifier repeats notify with success interval
