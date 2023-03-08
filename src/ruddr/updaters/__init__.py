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

"""Built in updaters and the updater base class"""

from .updater import (BaseUpdater, Updater, OneWayUpdater, TwoWayUpdater,
                      TwoWayZoneUpdater)

from . import duckdns
from . import freedns
from . import gandi
from . import he
from . import standard

updaters = {
    'duckdns': duckdns.DuckDNSUpdater,
    'freedns': freedns.FreeDNSUpdater,
    'gandi': gandi.GandiUpdater,
    'he': he.HEUpdater,
    'standard': standard.StandardUpdater,
}

__all__ = ['BaseUpdater', 'Updater', 'OneWayUpdater', 'TwoWayUpdater',
           'TwoWayZoneUpdater']
