import ipaddress

import doubles
import ruddr.manager

import pytest


@pytest.mark.parametrize('expected', [True, False])
def test_validate_notifier_type(mocker, notifier_factory, expected):
    """Test validate_notifier_type calls _validate_updater_or_notifier_type
    with 'notifier'"""
    validator = mocker.patch(
        "ruddr.manager._validate_updater_or_notifier_type",
        return_value=expected,
    )
    notifiers = {
        'test': notifier_factory(),
    }
    mocker.patch("ruddr.manager.notifiers.notifiers", new=notifiers)

    result = ruddr.manager.validate_notifier_type('testmod', 'testtype')

    assert result == expected
    assert validator.call_args == (
        ("notifier", notifiers, 'testmod', 'testtype'),
    )


@pytest.mark.parametrize('expected', [True, False])
def test_validate_updater_type(mocker, updater_factory, expected):
    """Test validate_updater_type calls _validate_updater_or_notifier_type
    with 'updater'"""
    validator = mocker.patch(
        "ruddr.manager._validate_updater_or_notifier_type",
        return_value=expected,
    )
    updaters = {
        'test': updater_factory(),
    }
    mocker.patch("ruddr.manager.updaters.updaters", new=updaters)

    result = ruddr.manager.validate_updater_type('testmod', 'testtype')

    assert result == expected
    assert validator.call_args == (
        ("updater", updaters, 'testmod', 'testtype'),
    )


def test_validate_updater_or_notifier_type_built_in():
    """Test _validate_updater_or_notifier_type with a "built-in" notifier"""
    notifiers = {
        'test': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, None, 'test'
    )
    assert result
    assert notifiers == {
        'test': doubles.FakeNotifier,
    }


def test_validate_updater_or_notifier_type_entry_point():
    """Test _validate_updater_or_notifier_type with an entry_point notifier"""
    notifiers = {
        'test': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, None, '_test'
    )
    assert result
    assert notifiers == {
        'test': doubles.FakeNotifier,
        '_test': ruddr.notifiers.static.StaticNotifier,
    }


def test_validate_updater_or_notifier_type_built_in_entry_point_conflict():
    """Test _validate_updater_or_notifier_type with a type matching both a
    built-in and an entry_point notifier and ensure built-in isn't replaced"""
    notifiers = {
        '_test': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, None, '_test'
    )
    assert result
    assert notifiers == {
        '_test': doubles.FakeNotifier,
    }


def test_validate_updater_or_notifier_type_no_such_type():
    """Test _validate_updater_or_notifier_type with a type that doesn't match
    anything"""
    notifiers = {
        'test': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, None, 'test_invalid'
    )
    assert not result
    assert notifiers == {
        'test': doubles.FakeNotifier,
    }


def test_validate_updater_or_notifier_type_class():
    """Test _validate_updater_or_notifier_type with a module and class"""
    notifiers = {
        'test': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, 'doubles', 'MockNotifier'
    )
    assert result
    assert notifiers == {
        'test': doubles.FakeNotifier,
        ('doubles', 'MockNotifier'): doubles.MockNotifier
    }


def test_validate_updater_or_notifier_type_module_not_importable():
    """Test _validate_updater_or_notifier_type with a module and class but
    module not importable"""
    notifiers = {
        'test': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, 'invalid', 'MockNotifier'
    )
    assert not result
    assert notifiers == {
        'test': doubles.FakeNotifier,
    }


def test_validate_updater_or_notifier_type_class_not_in_module():
    """Test _validate_updater_or_notifier_type with a module and class but
    class not in module"""
    notifiers = {
        'test': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, 'doubles', 'InvalidNotifier'
    )
    assert not result
    assert notifiers == {
        'test': doubles.FakeNotifier,
    }


def test_validate_updater_or_notifier_type_class_already_imported():
    """Test _validate_updater_or_notifier_type with a module and class already
    imported"""
    notifiers = {
        'test': doubles.FakeNotifier,
        ('doubles', 'MockNotifier'): doubles.MockNotifier
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, 'doubles', 'MockNotifier'
    )
    assert result
    assert notifiers == {
        'test': doubles.FakeNotifier,
        ('doubles', 'MockNotifier'): doubles.MockNotifier,
    }


def test_validate_updater_or_notifier_type_class_matches_built_in():
    """Test _validate_updater_or_notifier_type with a module and class where
    class name matches a built-in notifier"""
    notifiers = {
        'MockNotifier': doubles.FakeNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, 'doubles', 'MockNotifier'
    )
    assert result
    assert notifiers == {
        'MockNotifier': doubles.FakeNotifier,
        ('doubles', 'MockNotifier'): doubles.MockNotifier,
    }


def test_validate_updater_or_notifier_type_class_imported_matches_built_in():
    """Test _validate_updater_or_notifier_type with a module and class already
    imported where class name matches a built-in notifier"""
    notifiers = {
        'MockNotifier': doubles.FakeNotifier,
        ('doubles', 'MockNotifier'): doubles.MockNotifier,
    }
    result = ruddr.manager._validate_updater_or_notifier_type(
        'notifier', notifiers, 'doubles', 'MockNotifier'
    )
    assert result
    assert notifiers == {
        'MockNotifier': doubles.FakeNotifier,
        ('doubles', 'MockNotifier'): doubles.MockNotifier,
    }


@pytest.fixture
def mock_built_ins(mocker):
    """Fixture setting up the lists of built-in notifiers and updaters with
    mocks"""
    notifiers = {
        'test': doubles.FakeNotifier
    }
    updaters = {
        'test': doubles.MockBaseUpdater
    }
    mocker.patch("ruddr.manager.notifiers.notifiers", new=notifiers)
    mocker.patch("ruddr.manager.updaters.updaters", new=updaters)


def test_manager_creates_built_in_notifier(mock_built_ins):
    """Test that DDNSManager creates a notifier using type only and passes in
    its name and config"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'type': 'test',
                'test_key': 'test_val',
            }
        },
        updaters={
            'test_updater': {
                'type': 'test',
                'notifier': 'test_notifier',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    assert len(manager.notifiers) == 1
    assert type(manager.notifiers['test_notifier']) == doubles.FakeNotifier
    assert manager.notifiers['test_notifier'].name == 'test_notifier'
    assert manager.notifiers['test_notifier'].config['test_key'] == 'test_val'


def test_manager_creates_custom_notifier(mock_built_ins):
    """Test that DDNSManager creates a notifier using module and type and
    passes in its name and config"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'module': 'doubles',
                'type': 'FakeNotifier',
                'test_key': 'test_val',
            }
        },
        updaters={
            'test_updater': {
                'type': 'test',
                'notifier': 'test_notifier',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    assert len(manager.notifiers) == 1
    assert type(manager.notifiers['test_notifier']) == doubles.FakeNotifier
    assert manager.notifiers['test_notifier'].name == 'test_notifier'
    assert manager.notifiers['test_notifier'].config['test_key'] == 'test_val'


def test_manager_creates_built_in_updater(mock_built_ins):
    """Test that DDNSManager creates an updater using type only and passes in
    its name and config"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'type': 'test',
            }
        },
        updaters={
            'test_updater': {
                'type': 'test',
                'notifier': 'test_notifier',
                'test_key': 'test_val',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    assert len(manager.updaters) == 1
    assert type(manager.updaters['test_updater']) == doubles.MockBaseUpdater
    assert manager.updaters['test_updater'].name == 'test_updater'
    assert manager.updaters['test_updater'].config['test_key'] == 'test_val'
    assert manager.updaters['test_updater'].addrfile == manager.addrfile


def test_manager_creates_custom_updater(mock_built_ins):
    """Test that DDNSManager creates an updater using module and type and
    passes in its name and config"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'type': 'test',
            }
        },
        updaters={
            'test_updater': {
                'module': 'doubles',
                'type': 'MockBaseUpdater',
                'notifier': 'test_notifier',
                'test_key': 'test_val',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    assert len(manager.updaters) == 1
    assert type(manager.updaters['test_updater']) == doubles.MockBaseUpdater
    assert manager.updaters['test_updater'].name == 'test_updater'
    assert manager.updaters['test_updater'].config['test_key'] == 'test_val'
    assert manager.updaters['test_updater'].addrfile == manager.addrfile


def test_manager_attaches_notifier4(mock_built_ins):
    """Test that DDNSManager attaches a notifier to an updater with
    notifier4"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'type': 'test',
            }
        },
        updaters={
            'test_updater': {
                'type': 'test',
                'notifier4': 'test_notifier',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    notifier = manager.notifiers['test_notifier']
    updater = manager.updaters['test_updater']
    notifier.notify_ipv4(ipaddress.IPv4Address('1.2.3.4'))
    notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    assert updater.published_addresses == [ipaddress.IPv4Address('1.2.3.4')]


def test_manager_attaches_notifier6(mock_built_ins):
    """Test that DDNSManager attaches a notifier to an updater with
    notifier6"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'type': 'test',
            }
        },
        updaters={
            'test_updater': {
                'type': 'test',
                'notifier6': 'test_notifier',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    notifier = manager.notifiers['test_notifier']
    updater = manager.updaters['test_updater']
    notifier.notify_ipv4(ipaddress.IPv4Address('1.2.3.4'))
    notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    assert updater.published_addresses == [ipaddress.IPv6Network('1234::/64')]


def test_manager_attaches_notifier4_and_notifier6(mock_built_ins):
    """Test that DDNSManager attaches a notifier to an updater with
    notifier4 and notifier6"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'type': 'test',
            }
        },
        updaters={
            'test_updater': {
                'type': 'test',
                'notifier4': 'test_notifier',
                'notifier6': 'test_notifier',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    notifier = manager.notifiers['test_notifier']
    updater = manager.updaters['test_updater']
    notifier.notify_ipv4(ipaddress.IPv4Address('1.2.3.4'))
    notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    assert updater.published_addresses == [ipaddress.IPv4Address('1.2.3.4'),
                                           ipaddress.IPv6Network('1234::/64')]


def test_manager_attaches_different_notifier4_and_notifier6(mock_built_ins):
    """Test that DDNSManager attaches two notifiers to an updater with
    different notifier4 and notifier6"""
    config = ruddr.Config(
        main={},
        notifiers={
            'test_notifier': {
                'type': 'test',
            },
            'test_notifier2': {
                'type': 'test',
            }
        },
        updaters={
            'test_updater': {
                'type': 'test',
                'notifier4': 'test_notifier',
                'notifier6': 'test_notifier2',
            }
        },
    )
    manager = ruddr.manager.DDNSManager(config)
    notifier = manager.notifiers['test_notifier']
    notifier2 = manager.notifiers['test_notifier2']
    updater = manager.updaters['test_updater']
    notifier.notify_ipv4(ipaddress.IPv4Address('1.2.3.4'))
    notifier.notify_ipv6(ipaddress.IPv6Network('1234::/64'))
    notifier2.notify_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    notifier2.notify_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.published_addresses == [ipaddress.IPv4Address('1.2.3.4'),
                                           ipaddress.IPv6Network('5678::/64')]


# TODO Test notifier that doesn't want IPv4 or IPv6 is not started with start
# TODO Test notifier that doesn't want IPv4 or IPv6 is not stopped with stop
# TODO Test notifier that doesn't want IPv4 or IPv6 is not called with
#  do_notify


# TODO Notifiers are stopped after one raises NotifierSetupError
