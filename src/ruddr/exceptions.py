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

"""All Ruddr exceptions"""


class RuddrException(Exception):
    """Base class for all Ruddr exceptions"""


class RuddrSetupError(RuddrException):
    """Base class for Ruddr exceptions that happen during startup"""


class ConfigError(RuddrSetupError):
    """Raised when the configuration is malformed or has other errors"""


class NotifierSetupError(RuddrSetupError):
    """Raised by a notifier when there is a fatal error during setup for
    persistent checks"""


class NotStartedError(RuddrException):
    """Raised when requesting an on-demand notify before starting the
    notifier"""


class NotifyError(RuddrException):
    """Notifiers should raise when an attempt to check the current IP address
    fails. Doing so triggers the retry mechanism."""


class PublishError(RuddrException):
    """Updaters should raise when an attempt to publish an update fails. Doing
    so triggers the retry mechanism."""


class FatalPublishError(PublishError):
    """Updaters should raise when an attempt to publish an update fails in a
    non-recoverable way. Doing so causes the updater to halt until the next
    time Ruddr is started."""
