"""Ruddr configuration parsing"""

import configparser

from manager import RuddrException


DEFAULT_ADDRFILE = '/var/lib/misc/ruddr.addrfile'


class ConfigError(RuddrException):
    """Raised when the configuration is malformed or has other errors"""


class ConfigReader:
    """Read the Ruddr configuration and store its contents.

    :param configfile: Path to the configuration file
    """

    def __init__(self, configfile):
        #: Global configuration (from the ``[ruddr]`` section)
        self.main = dict()

        #: Notifier configurations (from ``[notifier.<name>]`` sections). Keys
        #: are notifier names, values are configuration dicts.
        self.notifiers = dict()

        #: Updater configurations (from ``[updater.<name>]`` sections). Keys
        #: are updater names, values are configuration dicts.
        self.updaters = dict()

        self._read_file(configfile)

    def _read_file(self, configfile):
        """Read configuration in from the named file

        :param configfile: Path to the configuration file
        """
        config = configparser.ConfigParser()
        try:
            with open(configfile, 'r') as f:
                config.read_file(f)
        except OSError as e:
            raise config.ConfigError("Could not read config file %s: %s" %
                                     (configfile, e.strerror)) from e
        except configparser.Error as e:
            raise config.ConfigError("Could not read config file %s: %s" %
                                     (configfile, e)) from e

        for section in config:
            if section == 'ruddr':
                self.main = dict(config[section])
                continue

            kind, _, name = section.partition('.')
            if kind == 'notifier':
                self.notifiers[name] = dict(config[section])
            elif kind == 'updater':
                self.updaters[name] = dict(config[section])
            else:
                raise config.ConfigError("Config section %s is not a notifier "
                                         "or updater section" % section)

        if 'addrfile' not in self.main:
            self.main['addrfile'] = DEFAULT_ADDRFILE
