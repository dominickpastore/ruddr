"""Built in notifiers and the notifier base class"""

from .notifier import Notifier, SchedulerNotifier, Scheduled
from ._getifaceaddrs import get_iface_addrs

from . import timed
#TODO create these
#from . import web
#from . import static

notifiers = {
    'timed': timed.TimedNotifier,
    #'web': web.WebNotifier,
    #'static': static.StaticNotifier,
}

# systemd notifier only works if PyGObject is installed
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
    'get_iface_addrs',
]
