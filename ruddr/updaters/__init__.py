"""Built in updaters and the updater base class"""

from .updater import PublishError, Updater

from . import gandi
from . import he

updaters = {
    'gandi': gandi.GandiUpdater,
    'he': he.HEUpdater,
}

__all__ = ['Updater', 'PublishError', 'updaters']
