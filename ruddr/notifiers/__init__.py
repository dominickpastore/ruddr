"""Built in notifiers and the notifier base class"""

from .notifier import BaseNotifier, Notifier
from ._getifaceaddrs import get_iface_addrs

from . import timed
from . import web
from . import static

notifiers = {
    'timed': timed.TimedNotifier,
    'web': web.WebNotifier,
    'static': static.StaticNotifier,
}

# systemd notifier only works if PyGObject is installed
try:
    from . import systemd
except ImportError:
    pass
else:
    notifiers['systemd'] = systemd.SystemdNotifier

__all__ = [
    'BaseNotifier',
    'Notifier',
    'get_iface_addrs',
]
