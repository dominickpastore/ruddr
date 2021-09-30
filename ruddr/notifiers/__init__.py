"""Build in notifiers and the notifier base class"""

from .notifier import Notifier, SchedulerNotifier, Scheduled
from ._getifaceaddrs import get_iface_addrs

#TODO create this
from . import web

notifiers = {
    'web': web.WebNotifier,
}

try:
    from . import systemd
except ImportError:
    pass
else:
    notifiers['systemd'] = systemd.SystemdNotifier

__all__ = [
    'Notifier',
    'SchedulerNotifier',
    'Scheduled',
    'notifiers',
    'get_iface_addrs',
]
