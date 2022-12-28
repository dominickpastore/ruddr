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
