#  Ruddr - Robotic Updater for Dynamic DNS Records
#  Copyright (C) 2023 Dominick C. Pastore
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import pytest

import doubles


def test_setup_teardown_not_implemented(advance):
    """Test starting, initial check, and teardown works when setup and teardown
    not implemented"""
    notifier = doubles.MockNotifier(
        'mock_notifier',
        dict(),
        setup_implemented=False,
        teardown_implemented=False,
    )
    notifier.set_check_intervals(retry_min_interval=1,
                                 retry_max_interval=5)

    assert notifier.call_sequence == []
    notifier.start()
    notifier.join_first_check()
    assert notifier.call_sequence == ['setup', 'check']
    advance.by(10)

    assert advance.count_running() == 0, "Unexpected checks pending"
    assert notifier.call_sequence == ['setup', 'check']
    notifier.stop()
    assert advance.count_running() == 0, "Unexpected pending checks after stop"
    assert notifier.call_sequence == ['setup', 'check', 'teardown']


def test_check_not_implemented(advance):
    """Test starting and teardown works when check_once not implemented"""
    notifier = doubles.MockNotifier(
        'mock_notifier',
        dict(),
        check_implemented=False,
    )
    notifier.set_check_intervals(retry_min_interval=1,
                                 retry_max_interval=5)

    assert notifier.call_sequence == []
    notifier.start()
    notifier.join_first_check()
    assert notifier.call_sequence == ['setup', 'check']
    advance.by(10)

    assert advance.count_running() == 0, "Unexpected checks pending"
    assert notifier.call_sequence == ['setup', 'check']
    notifier.stop()
    assert advance.count_running() == 0, "Unexpected pending checks after stop"
    assert notifier.call_sequence == ['setup', 'check', 'teardown']


def test_setup_teardown_not_implemented_with_scheduled_checks(advance):
    """Test starting, initial check, and teardown works when setup and teardown
    not implemented"""
    notifier = doubles.MockNotifier(
        'mock_notifier',
        dict(),
        setup_implemented=False,
        teardown_implemented=False,
    )
    notifier.set_check_intervals(retry_min_interval=1,
                                 retry_max_interval=5,
                                 success_interval=7)

    assert notifier.call_sequence == []
    notifier.start()
    notifier.join_first_check()
    assert notifier.call_sequence == ['setup', 'check']
    advance.by(6)

    notifier.do_notify()
    assert notifier.check_count == 2
    advance.by(7)
    assert notifier.check_count == 3
    advance.by(6)

    assert notifier.call_sequence == ['setup',
                                      'check', 'check', 'check']
    notifier.stop()
    assert advance.count_running() == 0, "Unexpected pending checks after stop"
    assert notifier.call_sequence == ['setup',
                                      'check', 'check', 'check',
                                      'teardown']


def test_default_check_intervals(advance):
    """Test that the default retry and success intervals are as expected"""
    notifier = doubles.MockNotifier(
        'mock_notifier',
        dict(),
        [False, False, False, False, False, False, False, False, False, False,
         True],
    )

    assert notifier.call_sequence == []
    notifier.start()
    notifier.join_first_check()
    assert notifier.call_sequence == ['setup', 'check']
    advance.by(300)

    assert notifier.check_count == 2
    advance.by(600)
    assert notifier.check_count == 3
    advance.by(1200)
    assert notifier.check_count == 4
    advance.by(2400)
    assert notifier.check_count == 5
    advance.by(4800)
    assert notifier.check_count == 6
    advance.by(9600)
    assert notifier.check_count == 7
    advance.by(19200)
    assert notifier.check_count == 8
    advance.by(38400)
    assert notifier.check_count == 9
    advance.by(76800)
    assert notifier.check_count == 10
    advance.by(86400)
    assert notifier.check_count == 11
    advance.by(100000)

    assert advance.count_running() == 0, "Unexpected checks pending"
    assert notifier.teardown_count == 0
    assert notifier.check_count == 11
    notifier.stop()
    assert advance.count_running() == 0, "Unexpected pending checks after stop"
    assert notifier.setup_count == 1
    assert notifier.check_count == 11
    assert notifier.teardown_count == 1


def test_set_intervals_from_config(advance):
    """Test that the retry and success intervals can be overridden by config"""
    notifier = doubles.MockNotifier(
        'mock_notifier',
        dict(),
        [False, False, False, False, True, True],
    )
    notifier.set_check_intervals(retry_min_interval=300,
                                 retry_max_interval=86400,
                                 success_interval=0,
                                 config={
                                     'retry_min_interval': '1',
                                     'retry_max_interval': '5',
                                     'interval': '7',
                                 })

    assert notifier.call_sequence == []
    notifier.start()
    notifier.join_first_check()
    assert notifier.call_sequence == ['setup', 'check']
    advance.by(1)

    assert notifier.check_count == 2
    advance.by(2)
    assert notifier.check_count == 3
    advance.by(4)
    assert notifier.check_count == 4
    advance.by(5)
    assert notifier.check_count == 5
    advance.by(10)

    assert advance.count_running() == 0, "Unexpected checks pending"
    assert notifier.teardown_count == 0
    assert notifier.check_count == 5
    notifier.stop()
    assert advance.count_running() == 0, "Unexpected pending checks after stop"
    assert notifier.setup_count == 1
    assert notifier.check_count == 5
    assert notifier.teardown_count == 1


def test_config_not_override_zero_success_interval(advance):
    """Test that a zero success interval (no repeat) isn't overridden by
    config"""
    notifier = doubles.MockNotifier(
        'mock_notifier',
        dict(),
    )
    notifier.set_check_intervals(retry_min_interval=300,
                                 retry_max_interval=86400,
                                 success_interval=0,
                                 config={
                                     'retry_min_interval': '1',
                                     'retry_max_interval': '5',
                                     'interval': '7',
                                 })

    assert notifier.call_sequence == []
    notifier.start()
    notifier.join_first_check()
    assert notifier.call_sequence == ['setup', 'check']
    advance.by(100000)

    assert advance.count_running() == 0, "Unexpected checks pending"
    assert notifier.teardown_count == 0
    assert notifier.check_count == 1
    notifier.stop()
    assert advance.count_running() == 0, "Unexpected pending checks after stop"
    assert notifier.setup_count == 1
    assert notifier.check_count == 1
    assert notifier.teardown_count == 1


# Sequence is list of checks as tuples (successful, on_demand, interval_after)
# on_demand is ignored for the initial check
@pytest.mark.parametrize("sequence,polling", [
    # === Non-polling tests ===
    # setup, initial check, teardown
    ([
        (True, False, 10),
     ], False),
    # setup, initial check, on demand check, teardown
    ([
         (True, False, 10),
         (True, True, 10),
     ], False),
    # setup, initial check fails, retry succeeds, teardown
    ([
         (False, False, 1),
         (True, False, 10),
     ], False),
    # setup, initial check fails, on demand check before retry, retry doesn't
    # happen, teardown
    ([
         (False, False, 0.5),
         (True, True, 10),
     ], False),
    # setup, initial check fails, next check fails, next check passes, teardown
    ([
         (False, False, 1),
         (False, False, 2),
         (True, False, 10),
     ], False),
    # setup, initial check fails, next check fails, on demand check fails but
    # short timeout again, then teardown
    ([
         (False, False, 1),
         (False, False, 1.5),
         (False, True, 1),
         (True, False, 10),
     ], False),

    # === Polling tests ===
    # setup, initial check, on demand check, scheduled check, teardown, no more
    # check
    ([
         (True, False, 6),
         (True, True, 7),
         (True, False, 6),
     ], True),
    # setup, initial check, scheduled check, teardown, no more check
    ([
         (True, False, 7),
         (True, False, 6),
     ], True),
    # setup, initial check fails, retry succeeds, scheduled check, teardown
    ([
         (False, False, 1),
         (True, False, 7),
         (True, False, 6),
     ], True),
    # setup, initial check, scheduled check fails, retry succeeds, scheduled
    # check, teardown
    ([
         (True, False, 7),
         (False, False, 1),
         (True, False, 7),
         (True, False, 6),
     ], True),
    # setup, initial check fails, retry succeeds, on demand check, scheduled
    # check, teardown
    ([
         (False, False, 1),
         (True, False, 6),
         (True, True, 7),
         (True, False, 6),
     ], True),
    # setup, initial check fails, retry fails 3 times, retry succeeds,
    # scheduled check, teardown
    ([
         (False, False, 1),
         (False, False, 2),
         (False, False, 4),
         (False, False, 5),
         (True, False, 7),
         (True, False, 6),
     ], True),
    # setup, initial check fails, retry fails 4 times, teardown, no more check
    ([
         (False, False, 1),
         (False, False, 2),
         (False, False, 4),
         (False, False, 5),
         (False, False, 4),
     ], True),
    # setup, initial check fails, fails twice more, on demand check fails,
    # retry after minimum delay fails, retry succeeds, teardown
    ([
         (False, False, 1),
         (False, False, 2),
         (False, False, 3),
         (False, True, 1),
         (False, False, 2),
         (True, False, 6),
     ], True),
])
def test_notifier_sequence(sequence, polling, advance):
    notifier = doubles.MockNotifier(
        'mock_notifier',
        dict(),
        [c[0] for c in sequence],
    )
    if polling:
        notifier.set_check_intervals(retry_min_interval=1,
                                     retry_max_interval=5,
                                     success_interval=7)
    else:
        notifier.set_check_intervals(retry_min_interval=1,
                                     retry_max_interval=5)

    # Setup and first check
    assert notifier.call_sequence == []
    notifier.start()
    notifier.join_first_check()
    assert notifier.call_sequence == ['setup', 'check']
    advance.by(sequence[0][2])

    # Rest of the checks
    check_count = 1
    for _, on_demand, interval_after in sequence[1:]:
        if on_demand:
            notifier.do_notify()
        check_count += 1
        assert notifier.check_count == check_count
        advance.by(interval_after)

    # If not polling, no checks pending (e.g. no extra retry)
    if not polling:
        assert advance.count_running() == 0, "Unexpected checks pending"

    # Teardown and final validations
    assert notifier.teardown_count == 0
    notifier.stop()
    assert advance.count_running() == 0, "Unexpected pending checks after stop"
    assert notifier.setup_count == 1
    assert notifier.check_count == len(sequence)
    assert notifier.teardown_count == 1
