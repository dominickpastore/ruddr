import errno
import ipaddress

import pytest

import doubles
import ruddr
from ruddr import PublishError, FatalPublishError


@pytest.fixture
def mock_addrfile_factory(mocker, tmp_path):
    """Fixture that sets up and returns a mock Addrfile factory"""
    count = 0

    # Arguments set up the initial addresses. Should be of the form:
    # - <name>_set4=ipaddress.IPv4Address(...)|None
    # - <name>_set6=ipaddress.IPv6Network(...)|None
    # - <name>_inv4=ipaddress.IPv4Address(...)|None
    # - <name>_inv6=ipaddress.IPv6Network(...)|None
    def factory(**kwargs):
        nonlocal count
        count += 1
        wrapped_addrfile = ruddr.Addrfile(tmp_path / f"addrfile_{count}")

        for arg, val in kwargs.items():
            name, _, kind = arg.rpartition('_')
            if kind == 'set4':
                wrapped_addrfile.set_ipv4(name, val)
            elif kind == 'set6':
                wrapped_addrfile.set_ipv6(name, val)
            elif kind == 'inv4':
                wrapped_addrfile.invalidate_ipv4(name, val)
            elif kind == 'inv6':
                wrapped_addrfile.invalidate_ipv6(name, val)
            else:
                raise TypeError("Addrfile factory args must end in _set4, "
                                "_set6, _inv4, _inv6")

        addrfile_mock = mocker.MagicMock(spec_set=wrapped_addrfile,
                                         wraps=wrapped_addrfile)
        return addrfile_mock

    return factory


def test_initial_update_ipv4(mock_addrfile_factory, advance):
    """Test initial update updates IPv4 if not current and updates addrfile"""
    addrfile = mock_addrfile_factory(
        test_updater_inv4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile)
    updater.initial_update()

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('1.2.3.4')]
    assert updater.ipv6s_published == []
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == []
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []


def test_initial_update_ipv6(mock_addrfile_factory, advance):
    """Test initial update updates IPv6 if not current and updates addrfile"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_inv6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile)
    updater.initial_update()

    assert advance.count_running() == 0
    assert updater.ipv4s_published == []
    assert updater.ipv6s_published == [ipaddress.IPv6Network('1234::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == []
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]


def test_initial_update_not_necessary(mock_addrfile_factory, advance):
    """Test initial update does no updates if current"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile)
    updater.initial_update()

    assert advance.count_running() == 0
    assert updater.ipv4s_published == []
    assert updater.ipv6s_published == []
    assert addrfile.invalidate_ipv4.call_args_list == []
    assert addrfile.invalidate_ipv6.call_args_list == []
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_initial_update_retries_ipv4(mock_addrfile_factory, advance):
    """Test initial update retries IPv4 on failure, invalidating the address in
    the addrfile, even when IPv6 succeeds"""
    addrfile = mock_addrfile_factory(
        test_updater_inv4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_inv6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile,
                                  ipv4_errors=[PublishError, None])
    updater.initial_update()

    assert updater.ipv4s_published == [ipaddress.IPv4Address('1.2.3.4')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('1234::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]

    advance.by(300)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('1.2.3.4'),
                                       ipaddress.IPv4Address('1.2.3.4')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('1234::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]


def test_initial_update_retries_ipv6(mock_addrfile_factory, advance):
    """Test initial update retries IPv6 on failure, invalidating the address in
    the addrfile, even when IPv4 succeeds"""
    addrfile = mock_addrfile_factory(
        test_updater_inv4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_inv6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile,
                                  ipv6_errors=[PublishError, None])
    updater.initial_update()

    assert updater.ipv4s_published == [ipaddress.IPv4Address('1.2.3.4')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('1234::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('1.2.3.4')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('1234::/64'),
                                       ipaddress.IPv6Network('1234::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]


def test_initial_update_no_retry_after_fatal_ipv4(mock_addrfile_factory,
                                                  advance):
    """Test initial update stops retrying both address families after a fatal
    error in IPv4"""
    addrfile = mock_addrfile_factory(
        test_updater_inv4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_inv6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile,
                                  ipv4_errors=[FatalPublishError, None],
                                  ipv6_errors=[PublishError, None])
    updater.initial_update()

    # Don't assert IPv6 publish attempt was made for certain because it may not
    # happen until after IPv4 fatal error
    assert updater.ipv4s_published == [ipaddress.IPv4Address('1.2.3.4')]
    assert len(updater.ipv6s_published) <= 1
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.invalidate_ipv6.call_count <= 1
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('1.2.3.4')]
    assert len(updater.ipv6s_published) <= 1
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('1.2.3.4')),),
    ]
    assert addrfile.invalidate_ipv6.call_count <= 1
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_initial_update_no_retry_after_fatal_ipv6(mock_addrfile_factory,
                                                  advance):
    """Test initial update stops retrying both address families after a fatal
    error in IPv6"""
    addrfile = mock_addrfile_factory(
        test_updater_inv4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_inv6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile,
                                  ipv4_errors=[PublishError, None],
                                  ipv6_errors=[FatalPublishError, None])
    updater.initial_update()

    # Don't assert IPv4 publish attempt was made for certain because it may not
    # happen until after IPv6 fatal error
    assert len(updater.ipv4s_published) <= 1
    assert updater.ipv6s_published == [ipaddress.IPv6Network('1234::/64')]
    assert addrfile.invalidate_ipv4.call_count <= 1
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert advance.count_running() == 0
    assert len(updater.ipv4s_published) <= 1
    assert updater.ipv6s_published == [ipaddress.IPv6Network('1234::/64')]
    assert addrfile.invalidate_ipv4.call_count <= 1
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('1234::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv4_succeeds(mock_addrfile_factory, advance):
    """Test update_ipv4 publishes address if not current and invalidates and
    updates addrfile"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile)
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]


def test_update_ipv6_succeeds(mock_addrfile_factory, advance):
    """Test update_ipv6 publishes address if not current and invalidates and
    updates addrfile"""
    addrfile = mock_addrfile_factory(
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile)
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert advance.count_running() == 0
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]


def test_update_ipv4_same_addr(mock_addrfile_factory, advance):
    """Test update_ipv4 does not publish same address that's already
    published"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile)
    updater.update_ipv4(ipaddress.IPv4Address('1.2.3.4'))

    assert advance.count_running() == 0
    assert updater.ipv4s_published == []
    assert addrfile.invalidate_ipv4.call_args_list == []
    assert addrfile.set_ipv4.call_args_list == []


def test_update_ipv6_same_addr(mock_addrfile_factory, advance):
    """Test update_ipv6 does not publish same address that's already
    published"""
    addrfile = mock_addrfile_factory(
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater('test_updater', addrfile)
    updater.update_ipv6(ipaddress.IPv6Network('1234::/64'))

    assert advance.count_running() == 0
    assert updater.ipv6s_published == []
    assert addrfile.invalidate_ipv6.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv4_not_implemented(mock_addrfile_factory, advance):
    """Test update_ipv4 does not set address in addrfile when not
    implemented"""
    addrfile = mock_addrfile_factory()
    updater = doubles.MockUpdater('test_updater', addrfile,
                                  ipv4_implemented=False)
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.set_ipv4.call_args_list == []


def test_update_ipv6_not_implemented(mock_addrfile_factory, advance):
    """Test update_ipv6 does not set address in addrfile when not
    implemented"""
    addrfile = mock_addrfile_factory()
    updater = doubles.MockUpdater('test_updater', addrfile,
                                  ipv6_implemented=False)
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert advance.count_running() == 0
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv4_retries(mock_addrfile_factory, advance):
    """Test update_ipv4 retries after failure, even when IPv6 succeeds, and
    invalidates old address until succeeding, at which point it stops retrying
    and updates the addrfile"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, None]
    )
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]

    advance.by(600)
    assert advance.count_running() == 0

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]


def test_update_ipv6_retries(mock_addrfile_factory, advance):
    """Test update_ipv6 retries after failure, even when IPv4 succeeds, and
    invalidates old address until succeeding, at which point it stops retrying
    and updates the addrfile"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv6_errors=[PublishError, PublishError, None]
    )
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
    ]

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
    ]

    advance.by(600)
    assert advance.count_running() == 0

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]


def test_update_ipv4_retries_after_same(mock_addrfile_factory, advance):
    """Test update_ipv4 retries after failure at the originally scheduled time
    after another update for the same address"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, None]
    )
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []

    advance.by(100)
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []

    advance.by(200)
    assert advance.count_running() == 0

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]


def test_update_ipv6_retries_after_same(mock_addrfile_factory, advance):
    """Test update_ipv6 retries after failure at the originally scheduled time
    after another update for the same address"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv6_errors=[PublishError, None]
    )
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(100)
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(200)
    assert advance.count_running() == 0

    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]


def test_update_ipv4_retry_resets_after_new(mock_addrfile_factory, advance):
    """Test update_ipv4 retry interval returns to minimum after a new failed
    call"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, PublishError, PublishError,
                     None]
    )
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []

    advance.by(600)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []

    advance.by(1100)
    updater.update_ipv4(ipaddress.IPv4Address('6.7.8.9'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('6.7.8.9')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('6.7.8.9')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []

    advance.by(300)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('6.7.8.9'),
                                       ipaddress.IPv4Address('6.7.8.9')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('6.7.8.9')),),
        (('test_updater', ipaddress.IPv4Address('6.7.8.9')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('6.7.8.9')),),
    ]


def test_update_ipv6_retry_resets_after_new(mock_addrfile_factory, advance):
    """Test update_ipv6 retry interval returns to minimum after a new failed
    call"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv6_errors=[PublishError, PublishError, PublishError, PublishError,
                     None]
    )
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(600)

    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(1100)
    updater.update_ipv6(ipaddress.IPv6Network('6789::/64'))

    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('6789::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('6789::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert advance.count_running() == 0
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('6789::/64'),
                                       ipaddress.IPv6Network('6789::/64')]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('6789::/64')),),
        (('test_updater', ipaddress.IPv6Network('6789::/64')),),
    ]
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('6789::/64')),),
    ]


def test_update_ipv4_retry_stops_after_fatal(mock_addrfile_factory, advance):
    """Test update_ipv4 stops retrying (and update_ipv6 as well) after a
    FatalPublishError"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, FatalPublishError],
        ipv6_errors=[PublishError, PublishError, PublishError]
    )
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    advance.by(1)
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(600)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv6_retry_stops_after_fatal(mock_addrfile_factory, advance):
    """Test update_ipv6 stops retrying (and update_ipv4 as well) after a
    FatalPublishError"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, PublishError],
        ipv6_errors=[PublishError, PublishError, FatalPublishError]
    )
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))
    advance.by(1)
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(600)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv4_addrfile_write_error_1(mock_addrfile_factory, advance):
    """Test update_ipv4 stops retrying (and update_ipv6 as well) after a write
    error in the addrfile for .invalidate_ipv4"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, PublishError],
        ipv6_errors=[PublishError, PublishError, PublishError]
    )
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    advance.by(1)
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    addrfile.invalidate_ipv4.side_effect = OSError(errno.ETIMEDOUT, "timeout")
    advance.by(600)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv6_addrfile_write_error_1(mock_addrfile_factory, advance):
    """Test update_ipv6 stops retrying (and update_ipv4 as well) after a write
    error in the addrfile for .invalidate_ipv6"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, PublishError],
        ipv6_errors=[PublishError, PublishError, PublishError]
    )
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))
    advance.by(1)
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    addrfile.invalidate_ipv6.side_effect = OSError(errno.ETIMEDOUT, "timeout")
    advance.by(600)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv4_addrfile_write_error_2(mock_addrfile_factory, advance):
    """Test update_ipv4 stops retrying (and update_ipv6 as well) after a write
    error in the addrfile for .set_ipv4"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, None],
        ipv6_errors=[PublishError, PublishError, PublishError]
    )
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    advance.by(1)
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    addrfile.set_ipv4.side_effect = OSError(errno.ETIMEDOUT, "timeout")
    advance.by(600)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.set_ipv6.call_args_list == []


def test_update_ipv6_addrfile_write_error_2(mock_addrfile_factory, advance):
    """Test update_ipv6 stops retrying (and update_ipv4 as well) after a write
    error in the addrfile for .set_ipv6"""
    addrfile = mock_addrfile_factory(
        test_updater_set4=ipaddress.IPv4Address('1.2.3.4'),
        test_updater_set6=ipaddress.IPv6Network('1234::/64'),
    )
    updater = doubles.MockUpdater(
        'test_updater', addrfile,
        ipv4_errors=[PublishError, PublishError, PublishError],
        ipv6_errors=[PublishError, PublishError, None]
    )
    updater.update_ipv6(ipaddress.IPv6Network('5678::/64'))
    advance.by(1)
    updater.update_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    advance.by(300)

    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == []

    addrfile.set_ipv6.side_effect = OSError(errno.ETIMEDOUT, "timeout")
    advance.by(600)

    assert advance.count_running() == 0
    assert updater.ipv4s_published == [ipaddress.IPv4Address('5.6.7.8'),
                                       ipaddress.IPv4Address('5.6.7.8')]
    assert updater.ipv6s_published == [ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64'),
                                       ipaddress.IPv6Network('5678::/64')]
    assert addrfile.invalidate_ipv4.call_args_list == [
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
        (('test_updater', ipaddress.IPv4Address('5.6.7.8')),),
    ]
    assert addrfile.invalidate_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
    assert addrfile.set_ipv4.call_args_list == []
    assert addrfile.set_ipv6.call_args_list == [
        (('test_updater', ipaddress.IPv6Network('5678::/64')),),
    ]
