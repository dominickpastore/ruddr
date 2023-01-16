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


# TODO Add tests for _validate_updater_or_notifier_type. It can do updaters
#  only since the behavior is exactly the same for notifiers.
# TODO Type is built-in updater
# TODO Type is entry_point updater (added to updaters dict)
# TODO Type is built-in updater but entry_point with same name exists, built-in
#  takes priority
# TODO Type does not match built-in or entry_point updater
# TODO Module and type is importable (added to updaters dict)
# TODO Module and type is not importable
# TODO Module and type already in updaters dict
# TODO Module and type is importable, type matches built-in (added to updaters
#  dict)
# TODO Module and type already in updaters dict, type matches built-in


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
