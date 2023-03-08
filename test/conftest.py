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

import threading
from typing import List

import pytest

import doubles
import ruddr.addrfile


class VirtualTimer:
    """Drop-in for :class:`threading.Timer` that uses a virtual clock
    instead of wall time and isn't actually threaded. This allows for
    deterministic behavior: the function runs immediately when
    :meth:`start` or :meth:`advance` is called if the virtual time has
    exceeded the interval time."""

    def __init__(self, interval, function, args=None, kwargs=None):
        super().__init__()
        self._function = function
        self._args = args if args is not None else []
        self._kwargs = kwargs if kwargs is not None else {}
        self._interval = interval
        self._lock = threading.Lock()
        self._complete = False
        self._elapsed = 0.0

        self._started = False
        self.daemon = False

    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        with self._lock:
            self._elapsed = self._interval
            self._complete = True

    def advance(self, seconds):
        """Advance the virtual clock"""
        with self._lock:
            self._elapsed += seconds
            self._try_run()

    @property
    def remaining(self):
        """Number of seconds remaining, or None if timer is complete"""
        with self._lock:
            if self._complete:
                return None
            return max(self._interval - self._elapsed, 0)

    def _try_run(self):
        if self._complete:
            return
        if self._elapsed < self._interval:
            return
        self._function(*self._args, **self._kwargs)
        self._complete = True

    def start(self):
        with self._lock:
            if self._started:
                raise RuntimeError("Already started")
            self._try_run()


@pytest.fixture
def advance():
    """Patch threading.Timer to give us total control of time"""

    class Advancer:
        def __init__(self):
            self.timers: List[VirtualTimer] = []

        def new_timer(self, *args, **kwargs):
            """Create a new virtual timer under the control of this Advancer"""
            timer = VirtualTimer(*args, **kwargs)
            self.timers.append(timer)
            return timer

        def by_minimum_or(self, seconds: float):
            """Advance virtual time just long enough for at least one timer
            to expire or by the given number of seconds, whichever is less, and
            return the number of seconds leftover"""
            remaining_times = [seconds] + [t.remaining for t in self.timers
                                           if t.remaining is not None]
            to_advance = min(remaining_times)
            # Make copy of self.timers so newly created timers aren't advanced
            for timer in list(self.timers):
                timer.advance(to_advance)
            return seconds - to_advance

        def by_minimum(self):
            """Advance virtual time just long enough for at least one timer
            to expire"""
            self.by_minimum_or(float('inf'))

        def by(self, seconds: float):
            """Advance virtual time by the given number of seconds"""
            while seconds > 0:
                seconds = self.by_minimum_or(seconds)

        def until_done(self):
            """Advance virtual time until all timers have elapsed"""
            while any(t.remaining is not None for t in self.timers):
                self.by_minimum()

        def cancel_all(self):
            """Cancel all timers remaining"""
            for timer in self.timers:
                if timer.remaining is not None:
                    timer.cancel()

        def count_running(self):
            """Count the number of timers that have not completed"""
            return sum(t.remaining is not None for t in self.timers)

    advancer = Advancer()

    orig_timer = threading.Timer
    threading.Timer = advancer.new_timer

    yield advancer

    threading.Timer = orig_timer


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
            return doubles.MockBaseUpdater(f'mock_updater_{self._count}',
                                           **kwargs)
    return UpdaterFactory()


@pytest.fixture
def mock_updater(updater_factory):
    """Fixture creating a mock :class:`~ruddr.Updater` that keeps a list of
    IP addresses it receives"""
    return updater_factory()


@pytest.fixture
def empty_addrfile(tmp_path):
    """Fixture creating an empty :class:`~ruddr.Addrfile`"""
    return ruddr.addrfile.Addrfile(tmp_path / 'addrfile')


@pytest.fixture(scope='session')
def data_dir(tmp_path_factory):
    return str(tmp_path_factory.mktemp('data'))
