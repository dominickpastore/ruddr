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
        self._main: Dict[str, str] = main

        #: Notifier configurations (from ``[notifier.<name>]`` sections)
        self._notifiers: Dict[str, Dict[str, str]] = notifiers

        #: Updater configurations (from ``[updater.<name>]`` sections)
        self._updaters: Dict[str, Dict[str, str]] = updaters

        #: Whether the config has been finalized yet
        self._finalized = False

    def _check_finalized(self):
        """Raise an exception if the config is not finalized"""
        if not self._finalized:
            raise ConfigError("Tried to access config before it was finalized")

    @property
    def main(self):
        self._check_finalized()
        return self._main

    @property
    def notifiers(self):
        self._check_finalized()
        return self._notifiers

    @property
    def updaters(self):
        self._check_finalized()
        return self._updaters

    def _fill_defaults(self):
        """Fill in defaults if they are not yet set"""
        if 'datadir' not in self.main:
            self.main['datadir'] = DEFAULT_DATA_DIR
        if not os.path.isabs(self.main['datadir']):
            raise ConfigError("Config option 'datadir' cannot be a relative"
                              "path")

    def _validate_types(
        self,
        kind: str,
        config_dict: Dict[str, Dict[str, str]],
        validate_type: Callable[[Optional[str], str], bool],
    ) -> None:
        """Verify that updater or notifier types are assigned and that they are
        valid

        :param kind: ``'Updater'`` or ``'Notifier'``
        :param config_dict: The config dict for those items
        :param validate_type: A callable that validates the updater or notifier
                              names

        :raises ConfigError: if any type is missing or invalid
        """
        for name, config in config_dict.items():
            module = config.get('module')
            try:
                type_ = config['type']
            except KeyError:
                raise ConfigError(f"{kind} {name} requires a type") from None
            exists = validate_type(module, type_)
            if not exists and module is None:
                raise ConfigError(f"No built-in {kind} of type {type_}")
            elif not exists:
                raise ConfigError(f"{kind} module or class {module}.{type_} "
                                  "does not exist")

    def _validate_and_assign_notifiers(self) -> None:
        """Translate ``notifier`` keys on updaters to ``notifier4`` and
        ``notifier6`` and copy global notifiers into updater config if
        necessary. In the process, validate that all ``notifier{4|6}`` keys
        point to defined notifiers.

        :raises ConfigError: if the config is invalid
        """
        # Get default notifiers, ensure they exist, and error if "notifier" is
        #   set when "notifier4" and "notifier6" are both set
        if ('notifier' in self._main and
                'notifier4' in self._main and
                'notifier6' in self._main):
            raise ConfigError('Main Ruddr config does not need "notifier" when'
                              ' "notifier4" and "notifier6" are both set')
        try:
            g_notifier4 = self._main['notifier4']
        except KeyError:
            g_notifier4 = self._main.get('notifier')
        if g_notifier4 is not None and g_notifier4 not in self._notifiers:
            raise ConfigError("Notifier %s does not exist" % g_notifier4)
        try:
            g_notifier6 = self._main['notifier6']
        except KeyError:
            g_notifier6 = self._main.get('notifier')
        if g_notifier6 is not None and g_notifier6 not in self._notifiers:
            raise ConfigError("Notifier %s does not exist" % g_notifier6)

        for updater_name, updater_config in self._updaters.items():
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
            if notifier4 is not None and notifier4 not in self._notifiers:
                raise ConfigError("Notifier %s does not exist" % notifier4)

            try:
                notifier6 = updater_config['notifier6']
            except KeyError:
                notifier6 = updater_config.get('notifier')
            if notifier6 is not None and notifier6 not in self._notifiers:
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

    def _copy_globals(self) -> None:
        """Copy relevant global (e.g. ``[ruddr]``) config options into updater
        and notifier configs. For example, the data directory.

        Does not copy the global notifier(s), which are handled by
        :func:`_validate_and_assign_notifiers`.
        """
        for notifier_config in self._notifiers.values():
            notifier_config['datadir'] = self._main['datadir']
        for updater_config in self._updaters.values():
            updater_config['datadir'] = self._main['datadir']

    def finalize(self,
                 validate_notifier_type: Callable[[Optional[str], str], bool],
                 validate_updater_type: Callable[[Optional[str], str], bool]):
        """Used by :class:`~ruddr.DDNSManager` to finalize the configuration.
        This consists of validating the updater and notifier types, filling
        default values, and doing some normalization.

        :param validate_notifier_type: A callable to check if a notifier type
                                       is valid. First parameter is a module
                                       name, or ``None`` if it's a built-in
                                       notifier type. Second parameter is a
                                       class name or built-in notifier type
                                       name.
        :param validate_updater_type: A callable to check if an updater type is
                                      valid. Parameters are the same as above.
        :raises ConfigError: if the configuration is invalid
        """
        if self._finalized:
            return

        self._fill_defaults()
        self._validate_types('Updater', self._updaters, validate_updater_type)
        self._validate_types('Notifier', self._notifiers,
                             validate_notifier_type)
        self._validate_and_assign_notifiers()
        self._copy_globals()

        self._finalized = True


def _process_config(config: configparser.ConfigParser) -> Config:
    """Process the given :class:`~configparser.ConfigParser` into a
    :class:`Config`

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

    return Config(main, notifiers, updaters)

def read_file_path(filename: Union[str, pathlib.Path]) -> Config:
    """Read configuration from the named file or :class:`~pathlib.Path`

    :param filename: Filename or path to read from
    :raises ConfigError: if the config file cannot be read or is invalid
    :return: A :class:`Config` ready to be passed to
             :class:`~ruddr.DDNSManager`
    """
    try:
        with open(filename, 'r') as f:
            return read_file(f)
    except OSError as e:
        raise ConfigError("Could not read config file %s: %s" %
                          (filename, e.strerror)) from e

def read_file(configfile: TextIO) -> Config:
    """Read configuration in from the named file

    :param configfile: Filelike object to read the config from
    :raises ConfigError: if the config file cannot be read or is invalid
    :return: A :class:`Config` ready to be passed to
             :class:`~ruddr.DDNSManager`
    """
    config = configparser.ConfigParser()
    try:
        config.read_file(configfile)
    except configparser.Error as e:
        raise ConfigError("Error in config file: %s" % e) from e

    return _process_config(config)
