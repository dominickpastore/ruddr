"""Build in notifiers and the notifier base class"""

from .notifier import NotifyError, Notifier, SchedulerNotifier, Scheduled
from ._get_iface_addrs import get_iface_addrs

#TODO create these
from . import systemd
from . import web

notifiers = {
    'systemd': systemd.SystemdNotifier,
    'web': web.WebNotifier,
}

__all__ = [
    'NotifyError',
    'Notifier',
    'SchedulerNotifier',
    'Scheduled',
    'notifiers',
    'get_iface_addrs',
]
