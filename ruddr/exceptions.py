"""All Ruddr exceptions"""


# TODO Redesign this. RuddrException becomes a base class for all Ruddr
# exceptions, period. New RuddrSetupError for exceptions raised during
# initialization and setup (ConfigError, NotifierSetupError). NotifyError for
# failed notify, PublishError for failed publish.


class RuddrException(Exception):
    """Base class for all Ruddr exceptions except PublishError (which should
    never be uncaught within Ruddr when raised). Whenever this is raised, a
    message should be logged first.
    """


class NotifyError(RuddrException):
    """Raised by a notifier's :meth:`~ruddr.Notifier.check_once` method or a
    scheduled method in a :class:`~ruddr.ScheduledNotifier` to signal an error.
    In the latter case, the method will be rescheduled using the failure
    interval."""


class NotifierSetupError(RuddrException):
    """Raised by a notifier when there is a fatal error during setup for
    persistent checks"""


class ConfigError(RuddrException):
    """Raised when the configuration is malformed or has other errors"""


class PublishError(Exception):
    """Updaters should raise when an attempt to publish an update fails. Doing
    so triggers the retry mechanism."""


class FatalPublishError(PublishError):
    """Updaters should raise when an attempt to publish an update fails in a
    non-recoverable way. Doing so causes the updater to halt until the next
    time Ruddr is started."""
