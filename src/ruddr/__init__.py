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

"""Ruddr, the Robotic Updater for Dynamic DNS Records

Top-level module, containing classes and objects useful to custom notifiers and
updaters.
"""

from .addrfile import Addrfile
from .configuration import Config, read_config, read_config_from_path
from .exceptions import (RuddrException, RuddrSetupError, ConfigError,
                         NotifierSetupError, NotStartedError, NotifyError,
                         PublishError, FatalPublishError)
from .manager import DDNSManager
from .notifiers import BaseNotifier, Notifier
from .updaters import (Updater, BaseUpdater, OneWayUpdater, TwoWayUpdater,
                       TwoWayZoneUpdater)
