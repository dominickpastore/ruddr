import ipaddress
from typing import Dict

import doubles
import ruddr.manager

import pytest


class TestUpdaterNotifierValidation:
    @pytest.mark.parametrize('expected', [True, False])
    def test_validate_notifier_type(self, mocker, notifier_factory, expected):
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
    def test_validate_updater_type(self, mocker, updater_factory, expected):
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

    def test_built_in(self):
        """Test _validate_updater_or_notifier_type with a "built-in"
        notifier"""
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

    def test_entry_point(self):
        """Test _validate_updater_or_notifier_type with an entry_point
        notifier"""
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

    def test_built_in_entry_point_conflict(self):
        """Test _validate_updater_or_notifier_type with a type matching both a
        built-in and an entry_point notifier and ensure built-in isn't
        replaced"""
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

    def test_no_such_type(self):
        """Test _validate_updater_or_notifier_type with a type that doesn't
        match anything"""
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

    def test_module_and_class(self):
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

    def test_module_not_importable(self):
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

    def test_class_not_in_module(self):
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

    def test_module_and_class_already_imported(self):
        """Test _validate_updater_or_notifier_type with a module and class
        already imported"""
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

    def test_class_matches_built_in(self):
        """Test _validate_updater_or_notifier_type with a module and class
        where class name matches a built-in notifier"""
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

    def test_class_imported_matches_built_in(self):
        """Test _validate_updater_or_notifier_type with a module and class
        already imported where class name matches a built-in notifier"""
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


class TestDDNSManager:
    def _new_mock_notifier(self, name: str, *args, **kwargs):
        """Keep track of MockNotifiers created using mock_built_ins"""
        notifier = doubles.MockNotifier(name, *args, **kwargs)
        self.notifiers[name] = notifier
        return notifier

    @pytest.fixture(autouse=True)
    def mock_built_ins(self, mocker):
        """Fixture setting up the lists of built-in notifiers and updaters with
        mocks"""
        self.notifiers: Dict[str, doubles.MockNotifier] = dict()

        notifiers = {
            'test': doubles.FakeNotifier,
            'mock': self._new_mock_notifier,
        }
        updaters = {
            'test': doubles.MockBaseUpdater,
        }

        mocker.patch("ruddr.manager.notifiers.notifiers", new=notifiers)
        mocker.patch("ruddr.manager.updaters.updaters", new=updaters)

    def test_manager_creates_built_in_notifier(self):
        """Test that DDNSManager creates a notifier using type only and passes
        in its name and config"""
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
        assert (manager.notifiers['test_notifier'].config['test_key'] ==
                'test_val')

    def test_manager_creates_custom_notifier(self):
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
        assert (type(manager.notifiers['test_notifier']) ==
                doubles.FakeNotifier)
        assert manager.notifiers['test_notifier'].name == 'test_notifier'
        assert (manager.notifiers['test_notifier'].config['test_key'] ==
                'test_val')

    def test_manager_creates_built_in_updater(self):
        """Test that DDNSManager creates an updater using type only and passes
        in its name and config"""
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
        assert (type(manager.updaters['test_updater']) ==
                doubles.MockBaseUpdater)
        assert manager.updaters['test_updater'].name == 'test_updater'
        assert (manager.updaters['test_updater'].config['test_key'] ==
                'test_val')
        assert manager.updaters['test_updater'].addrfile == manager.addrfile

    def test_manager_creates_custom_updater(self):
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
        assert (type(manager.updaters['test_updater']) ==
                doubles.MockBaseUpdater)
        assert manager.updaters['test_updater'].name == 'test_updater'
        assert (manager.updaters['test_updater'].config['test_key'] ==
                'test_val')
        assert manager.updaters['test_updater'].addrfile == manager.addrfile

    def test_manager_attaches_notifier4(self):
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
        assert updater.published_addresses == [
            ipaddress.IPv4Address('1.2.3.4'),
        ]

    def test_manager_attaches_notifier6(self):
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
        assert updater.published_addresses == [
            ipaddress.IPv6Network('1234::/64'),
        ]

    def test_manager_attaches_notifier4_and_notifier6(self):
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
        assert updater.published_addresses == [
            ipaddress.IPv4Address('1.2.3.4'),
            ipaddress.IPv6Network('1234::/64'),
        ]

    def test_manager_attaches_different_notifier4_and_notifier6(self):
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
        assert updater.published_addresses == [
            ipaddress.IPv4Address('1.2.3.4'),
            ipaddress.IPv6Network('5678::/64'),
        ]

    @pytest.mark.parametrize('skipping', ['ipv4', 'ipv6', None])
    def test_notifier_not_started_when_not_attached(self, skipping):
        """Test that DDNSManager doesn't start a notifier that's not attached
        to any updater. Skipping parameter determines whether it's not attached
        because it's skipping the family it's attached to or whether it's
        simply not attached at all."""
        notifiers = {
            'test_notifier': {
                'type': 'mock',
            },
            'test_notifier2': {
                'type': 'mock',
            }
        }
        updaters = {
            'test_updater': {
                'type': 'test',
            }
        }
        if skipping == 'ipv4':
            notifiers['test_notifier']['skip_ipv4'] = 'true'
            updaters['test_updater']['notifier4'] = 'test_notifier'
            updaters['test_updater']['notifier6'] = 'test_notifier2'
        elif skipping == 'ipv6':
            notifiers['test_notifier']['skip_ipv6'] = 'true'
            updaters['test_updater']['notifier6'] = 'test_notifier'
            updaters['test_updater']['notifier4'] = 'test_notifier2'
        else:
            updaters['test_updater']['notifier'] = 'test_notifier2'

        config = ruddr.Config(main={}, notifiers=notifiers, updaters=updaters)
        manager = ruddr.manager.DDNSManager(config)
        assert len(self.notifiers) == 2

        manager.start()
        assert self.notifiers['test_notifier'].setup_count == 0
        assert self.notifiers['test_notifier2'].setup_count == 1
        assert self.notifiers['test_notifier'].check_count == 0
        assert self.notifiers['test_notifier2'].check_count == 1
        assert self.notifiers['test_notifier'].teardown_count == 0
        assert self.notifiers['test_notifier2'].teardown_count == 0

        manager.do_notify()
        assert self.notifiers['test_notifier'].setup_count == 0
        assert self.notifiers['test_notifier2'].setup_count == 1
        assert self.notifiers['test_notifier'].check_count == 0
        assert self.notifiers['test_notifier2'].check_count == 2
        assert self.notifiers['test_notifier'].teardown_count == 0
        assert self.notifiers['test_notifier2'].teardown_count == 0

        manager.stop()
        assert self.notifiers['test_notifier'].setup_count == 0
        assert self.notifiers['test_notifier2'].setup_count == 1
        assert self.notifiers['test_notifier'].check_count == 0
        assert self.notifiers['test_notifier2'].check_count == 2
        assert self.notifiers['test_notifier'].teardown_count == 0
        assert self.notifiers['test_notifier2'].teardown_count == 1

    @pytest.mark.parametrize('which', ['test_notifier', 'test_notifier2'])
    def test_notifiers_stopped_after_error(self, which):
        """Test that DDNSManager stops all notifiers if one notifier raises
        NotifierSetupError"""
        notifiers = {
            'test_notifier': {
                'type': 'mock',
            },
            'test_notifier2': {
                'type': 'mock',
            }
        }
        updaters = {
            'test_updater': {
                'type': 'test',
                'notifier4': 'test_notifier',
                'notifier6': 'test_notifier2',
            }
        }

        config = ruddr.Config(main={}, notifiers=notifiers, updaters=updaters)
        manager = ruddr.manager.DDNSManager(config)
        assert len(self.notifiers) == 2

        self.notifiers[which].setup_error = True

        with pytest.raises(ruddr.NotifierSetupError):
            manager.start()
        assert self.notifiers['test_notifier2'].stop_count == 1
        assert self.notifiers['test_notifier'].stop_count == 1
