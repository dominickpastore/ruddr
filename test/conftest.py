from typing import List

import pytest

import threading


# TODO Make this not use threading to maximize determinism
class VirtualTimer(threading.Timer):
    """Drop-in for :class:`threading.Timer` that uses a virtual clock
    instead of wall time"""

    def __init__(self, interval, function, args=None, kwargs=None):
        super().__init__()
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.interval = interval
        self.cond = threading.Condition()
        self.complete = False
        self.elapsed = 0.0

    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        with self.cond:
            self.elapsed = self.interval
            self.complete = True
            self.cond.notify_all()

    def advance(self, seconds):
        """Advance the virtual clock"""
        with self.cond:
            self.elapsed += seconds
            self.cond.notify_all()

    @property
    def remaining(self):
        """Number of seconds remaining, or None if timer is complete"""
        with self.cond:
            if self.complete:
                return None
            return max(self.interval - self.elapsed, 0)

    def run(self):
        with self.cond:
            while self.elapsed < self.interval:
                self.cond.wait()
            if not self.complete:
                self.function(*self.args, **self.kwargs)
            self.complete = True


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

        def by_minimum_or(self, seconds: float):
            """Advance virtual time just long enough for at least one timer
            to expire or by the given number of seconds, whichever is less, and
            return the number of seconds leftover"""
            to_advance = min(
                seconds,
                *(t.remaining for t in self.timers if t.remaining is not None),
            )
            for timer in self.timers:
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

    advancer = Advancer()

    orig_timer = threading.Timer
    threading.Timer = VirtualTimer

    yield advancer

    # TODO need to cancel timers? Or should we verify that all timers are
    #  done?
    threading.Timer = orig_timer
