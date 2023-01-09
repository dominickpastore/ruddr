import pytest
import ipaddress

import ruddr


def test_require_and_skip_ipv4(notifier_factory):
    """Test requiring IPv4 when skipped is error"""
    with pytest.raises(ruddr.ConfigError):
        notifier_factory(ipv4_required='true', skip_ipv4='true')


def test_require_and_skip_ipv6(notifier_factory):
    """Test requiring IPv6 when skipped is error"""
    with pytest.raises(ruddr.ConfigError):
        notifier_factory(ipv6_required='true', skip_ipv6='true')


def test_require_ipv4_and_skip_ipv6(notifier_factory, mock_updater):
    """Test requiring IPv4 when IPv6 skipped is okay"""
    fake_notifier = notifier_factory(ipv4_required='true', skip_ipv6='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)

    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    assert mock_updater.published_addresses == [
        ipaddress.IPv4Address('10.20.30.40'),
    ]


def test_require_ipv6_and_skip_ipv4(notifier_factory, mock_updater):
    """Test requiring IPv6 when IPv4 skipped is okay"""
    fake_notifier = notifier_factory(ipv6_required='true', skip_ipv4='true')
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)

    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    assert mock_updater.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
    ]


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


def test_ipv4_ready_false_attach_ipv6(notifier_factory, mock_updater):
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


def test_ipv6_ready_false_attach_ipv4(notifier_factory, mock_updater):
    """Test attaching only IPv4 updater with ipv6_ready set to false"""
    fake_notifier = notifier_factory(ipv6_ready='false')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    # Well-written notifiers don't call notify_ipv6() when want_ipv6() is False

    assert mock_updater.published_addresses == [
        ipaddress.IPv4Address('10.20.30.40'),
        ipaddress.IPv4Address('50.60.70.80'),
    ]


def test_want_ipv4_false(notifier_factory, mock_updater):
    """Test want_ipv4 is true when ipv4 update function not attached"""
    fake_notifier = notifier_factory()
    assert fake_notifier.want_ipv4() == False


def test_want_ipv4_true(notifier_factory, mock_updater):
    """Test want_ipv4 is true when ipv4 update function attached"""
    fake_notifier = notifier_factory()
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    assert fake_notifier.want_ipv4() == True


def test_want_ipv6_false(notifier_factory, mock_updater):
    """Test want_ipv6 is true when ipv6 update function not attached"""
    fake_notifier = notifier_factory()
    assert fake_notifier.want_ipv6() == False


def test_want_ipv6_true(notifier_factory, mock_updater):
    """Test want_ipv6 is true when ipv6 update function attached"""
    fake_notifier = notifier_factory()
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    assert fake_notifier.want_ipv6() == True


def test_need_ipv4_false_not_required(notifier_factory, mock_updater):
    """Test need_ipv4 is false when updater attached but not required"""
    fake_notifier = notifier_factory(ipv4_required='false')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    assert fake_notifier.need_ipv4() == False


def test_need_ipv4_false_no_updater(notifier_factory, mock_updater):
    """Test need_ipv4 is false when required but no updater attached"""
    fake_notifier = notifier_factory(ipv4_required='true')
    assert fake_notifier.need_ipv4() == False


def test_need_ipv4_true(notifier_factory, mock_updater):
    """Test need_ipv4 is true when required and updater attached"""
    fake_notifier = notifier_factory(ipv4_required='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    assert fake_notifier.need_ipv4() == True


def test_need_ipv6_false_not_required(notifier_factory, mock_updater):
    """Test need_ipv6 is false when updater attached but not required"""
    fake_notifier = notifier_factory(ipv6_required='false')
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    assert fake_notifier.need_ipv6() == False


def test_need_ipv6_false_no_updater(notifier_factory, mock_updater):
    """Test need_ipv6 is false when required but no updater attached"""
    fake_notifier = notifier_factory(ipv6_required='true')
    assert fake_notifier.need_ipv6() == False


def test_need_ipv6_true(notifier_factory, mock_updater):
    """Test need_ipv6 is true when required and updater attached"""
    fake_notifier = notifier_factory(ipv6_required='true')
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    assert fake_notifier.need_ipv6() == True


def test_defaults(notifier_factory, mock_updater):
    """Test default config settings are IPv4 required, IPv6 not, neither
    skipped"""
    fake_notifier = notifier_factory()
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    assert fake_notifier.want_ipv4() == True
    assert fake_notifier.need_ipv4() == True
    assert fake_notifier.want_ipv6() == True
    assert fake_notifier.need_ipv6() == False


def test_skip_ipv4_attach_ipv4(notifier_factory, mock_updater):
    """Test attaching an updater for IPv4 and notifying when IPv4 is skipped
    does nothing"""
    fake_notifier = notifier_factory(skip_ipv4='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    # Well-behaved notifiers wouldn't notify_ipv4 when want_ipv4 is false, but
    # it must not cause problems
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    assert mock_updater.published_addresses == []


def test_skip_ipv4_attach_both(notifier_factory, mock_updater):
    """Test attaching an updater when IPv4 is skipped works for IPv6"""
    fake_notifier = notifier_factory(skip_ipv4='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    # Well-behaved notifiers wouldn't notify_ipv4 when want_ipv4 is false, but
    # it must not cause problems
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert mock_updater.published_addresses == [
        ipaddress.IPv6Network('1234::/64'),
        ipaddress.IPv6Network('5678::/64'),
    ]


def test_skip_ipv6_attach_ipv6(notifier_factory, mock_updater):
    """Test attaching an updater for IPv6 and notifying when IPv6 is skipped
    does nothing"""
    fake_notifier = notifier_factory(skip_ipv6='true')
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    assert not fake_notifier.want_ipv6()
    # Well-behaved notifiers wouldn't notify_ipv6 when want_ipv6 is false, but
    # it must not cause problems
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert mock_updater.published_addresses == []


def test_skip_ipv6_attach_both(notifier_factory, mock_updater):
    """Test attaching an updater when IPv6 is skipped works for IPv4"""
    fake_notifier = notifier_factory(skip_ipv6='true')
    fake_notifier.attach_ipv4_updater(mock_updater.update_ipv4)
    fake_notifier.attach_ipv6_updater(mock_updater.update_ipv6)
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    # Well-behaved notifiers wouldn't notify_ipv6 when want_ipv6 is false, but
    # it must not cause problems
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))

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
    # Well-behaved notifiers wouldn't notify_ipv4 when want_ipv4 is false
    # (especially when IPv4 isn't ready), but it must not cause problems
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('10.20.30.40'))
    fake_notifier.notify_ipv4(ipaddress.IPv4Address('50.60.70.80'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))

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
    # Well-behaved notifiers wouldn't notify_ipv4 when want_ipv4 is false
    # (especially when IPv4 isn't ready), but it must not cause problems
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    fake_notifier.notify_ipv6(ipaddress.IPv6Network('5678::/64'))

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
