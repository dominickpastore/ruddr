"""Ruddr configuration parsing"""

import configparser
import os.path
import pathlib
import sys

from typing import Dict, Callable, Union, TextIO, Optional

if sys.version_info < (3, 10):
    from importlib_metadata import version
else:
    from importlib.metadata import version

from .exceptions import ConfigError


USER_AGENT = f"ruddr/{version('ruddr')} (ruddr@dcpx.org)"


DEFAULT_DATA_DIR = '/var/lib/ruddr'


class Config:
    """Ruddr configuration data"""

    def __init__(self,
                 main: Dict[str, str],
                 notifiers: Dict[str, Dict[str, str]],
                 updaters: Dict[str, Dict[str, str]]):
        #: Dict containing global configuration (from the ``[ruddr]`` section)
        self.main: Dict[str, str] = main

        #: Notifier configurations (from ``[notifier.<name>]`` sections)
        self.notifiers: Dict[str, Dict[str, str]] = notifiers

        #: Update configurations (from ``[updater.<name>]`` sections)
        self.updaters: Dict[str, Dict[str, str]] = updaters


class ConfigReader:
    """A reader for Ruddr configuration that validates the config after it is
    read in.

    :param validate_notifier_type: A callable to check if a notifier type is
                                   valid. First parameter is a module name, or
                                   ``None`` if it's a built-in notifier type.
                                   Second parameter is a class name or built-in
                                   notifier type name.
    :param validate_updater_type: A callable to check if an updater type is
                                  valid. Parameters are the same as above.
    """

    def __init__(self,
                 validate_notifier_type: Callable[[Optional[str], str], bool],
                 validate_updater_type: Callable[[Optional[str], str], bool]):

        self._validate_notifier_type = validate_notifier_type
        self._validate_updater_type = validate_updater_type

    def _process_config(self, config: configparser.ConfigParser) -> Config:
        """Process the given :class:`~configparser.ConfigParser` into a
        :class:`Config`, validating and filling in defaults as necessary

        :param config: The configuration to process
        :raises ConfigError: if the configuration is invalid
        :returns: the processed and validated configuration
        """
        # Note: ConfigParser already handles catching duplicate sections and
        #   duplicate keys

        main: Dict[str, str] = dict()
        notifiers: Dict[str, Dict[str, str]] = dict()
        updaters: Dict[str, Dict[str, str]] = dict()

        for section in config:
            if section == 'ruddr':
                main.update(config[section])
                continue

            kind, _, name = section.partition('.')
            if kind == 'notifier':
                notifiers[name] = dict(config[section])
            elif kind == 'updater':
                updaters[name] = dict(config[section])
            else:
                raise ConfigError("Config section %s is not a notifier "
                                  "or updater section" % section)

        if 'datadir' not in main:
            main['datadir'] = DEFAULT_DATA_DIR
        if not os.path.isabs(main['datadir']):
            raise ConfigError("Config option 'datadir' cannot be a relative"
                              "path")

        result = Config(main, notifiers, updaters)
        self._validate_types(result)
        self._validate_and_assign_notifiers(result)
        self._copy_globals(result)
        return result

    def _validate_types(self, config: Config) -> None:
        """Verify that updater and notifier types are assigned and that they
        are valid

        :param config: The configuration to validate
        :raises ConfigError: if any type is missing or invalid
        """
        for updater_name, updater_config in config.updaters.items():
            updater_module = updater_config.get('module')
            try:
                updater_type = updater_config['type']
            except KeyError:
                raise ConfigError("Updater %s requires a type"
                                  % updater_name) from None
            exists = self._validate_updater_type(updater_module, updater_type)
            if not exists and updater_module is None:
                raise ConfigError("No built-in updater of type %s"
                                  % updater_type)
            elif not exists:
                raise ConfigError("Updater module or class %s.%s does not "
                                  "exist" % (updater_module, updater_type))

        for notifier_name, notifier_config in config.notifiers.items():
            notifier_module = notifier_config.get('module')
            try:
                notifier_type = notifier_config['type']
            except KeyError:
                raise ConfigError("Notifier %s requires a type"
                                  % notifier_name) from None
            exists = self._validate_notifier_type(notifier_module,
                                                  notifier_type)
            if not exists and notifier_module is None:
                raise ConfigError("No built-in notifier of type %s"
                                  % notifier_type)
            elif not exists:
                raise ConfigError("Notifier module or class %s.%s does not "
                                  "exist" % (notifier_module, notifier_type))

    def _validate_and_assign_notifiers(self, config: Config) -> None:
        """Translate ``notifier`` keys on updaters to ``notifier4`` and
        ``notifier6`` and copy global notifiers into updater config if
        necessary. In the process, validate that all ``notifier[4|6]`` keys
        point to defined notifiers.

        :param config: The config to assign notifiers on
        :raises ConfigError: if the config is invalid
        """
        # Get default notifiers, ensure they exist, and error if "notifier" is
        #   set when "notifier4" and "notifier6" are both set
        if ('notifier' in config.main and
                'notifier4' in config.main and
                'notifier6' in config.main):
            raise ConfigError('[ruddr] does not need "notifier" when '
                              '"notifier4" and "notifier6" are both set')
        try:
            g_notifier4 = config.main['notifier4']
        except KeyError:
            g_notifier4 = config.main.get('notifier')
        if g_notifier4 is not None and g_notifier4 not in config.notifiers:
            raise ConfigError("Notifier %s does not exist" % g_notifier4)
        try:
            g_notifier6 = config.main['notifier6']
        except KeyError:
            g_notifier6 = config.main.get('notifier')
        if g_notifier6 is not None and g_notifier6 not in config.notifiers:
            raise ConfigError("Notifier %s does not exist" % g_notifier6)

        for updater_name, updater_config in config.updaters.items():
            # Error if "notifier" is set when "notifier4" and "notifier6" are
            #   both also set
            if ('notifier' in updater_config and
                    'notifier4' in updater_config and
                    'notifier6' in updater_config):
                raise ConfigError('Updater %s does not need "notifier" when '
                                  '"notifier4" and "notifier6" are both set'
                                  % updater_name)

            try:
                notifier4 = updater_config['notifier4']
            except KeyError:
                notifier4 = updater_config.get('notifier')
            if notifier4 is not None and notifier4 not in config.notifiers:
                raise ConfigError("Notifier %s does not exist" % notifier4)

            try:
                notifier6 = updater_config['notifier6']
            except KeyError:
                notifier6 = updater_config.get('notifier')
            if notifier6 is not None and notifier6 not in config.notifiers:
                raise ConfigError("Notifier %s does not exist" % notifier6)

            # If no notifiers configured for updater, use default notifiers
            if notifier4 is None and notifier6 is None:
                if g_notifier4 is None and g_notifier6 is None:
                    raise ConfigError("No notifier is configured for updater "
                                      "%s and there are no default notifiers "
                                      "configured" % updater_name)
                else:
                    notifier4 = g_notifier4
                    notifier6 = g_notifier6

            try:
                del updater_config['notifier']
            except KeyError:
                pass
            updater_config['notifier4'] = notifier4
            updater_config['notifier6'] = notifier6

    def _copy_globals(self, config: Config) -> None:
        """Copy relevant global (``[ruddr]``) config options into updater and
        notifier configs, e.g. the data directory.

        Does not copy the global notifier(s), which are handled by
        :func:`_validate_and_assign_notifiers`.

        :param config: The config to modify
        """
        for notifier_config in config.notifiers.values():
            notifier_config['datadir'] = config.main['datadir']
        for updater_config in config.updaters.values():
            updater_config['datadir'] = config.main['datadir']

    def read_file_path(self, filename: Union[str, pathlib.Path]) -> Config:
        """Read configuration from the named file or :class:`~pathlib.Path`

        :param filename: Filename or path to read from
        :raises ConfigError: if the config file cannot be read or is invalid
        :returns: A validated configuration
        """
        try:
            with open(filename, 'r') as f:
                return self.read_file(f)
        except OSError as e:
            raise ConfigError("Could not read config file %s: %s" %
                              (filename, e.strerror)) from e

    def read_file(self, configfile: TextIO) -> Config:
        """Read configuration in from the named file

        :param configfile: Filelike object to read the config from
        :raises ConfigError: if the config file cannot be read or is invalid
        :returns: A validated configuration
        """
        config = configparser.ConfigParser()
        try:
            config.read_file(configfile)
        except configparser.Error as e:
            raise ConfigError("Error in config file: %s" % e) from e

        return self._process_config(config)
