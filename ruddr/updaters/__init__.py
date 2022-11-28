"""Built in updaters and the updater base class"""

from .updater import BaseUpdater, Updater, OneWayUpdater

from . import gandi
from . import he
from . import standard

updaters = {
    'gandi': gandi.GandiUpdater,
    'he': he.HEUpdater,
    'standard': standard.StandardUpdater,
}

__all__ = ['BaseUpdater', 'Updater', 'OneWayUpdater']
