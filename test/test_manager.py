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


# TODO Manager creates notifier with type only and passes in name and config
# TODO Manager creates notifier with module and type and passes in name and
#  config
# TODO Manager creates updater with type only and passes in name, config, and
#  addrfile
# TODO Manager creates updater with module and type and passes in name, config,
#  and addrfile


# TODO Notifier is attached to updater with notifier4
# TODO Notifier is attached to updater with notifier6
# TODO Notifier is attached to updater with notifier4 and notifier6
# TODO Notifier is attached to different updaters with notifier4 and notifier6


# TODO Test notifier that doesn't want IPv4 or IPv6 is not started with start
# TODO Test notifier that doesn't want IPv4 or IPv6 is not stopped with stop
# TODO Test notifier that doesn't want IPv4 or IPv6 is not called with
#  do_notify


# TODO Notifiers are stopped after one raises NotifierSetupError
