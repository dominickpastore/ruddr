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

"""Built in notifiers and the notifier base class"""

from .notifier import BaseNotifier, Notifier

from . import iface
from . import web
from . import static

notifiers = {
    'iface': iface.IFaceNotifier,
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
]
