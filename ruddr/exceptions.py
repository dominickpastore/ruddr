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
