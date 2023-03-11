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

"""DDNS Manager: Initializes notifiers and updaters and manages the addrfile"""

import importlib
import logging
import os.path
import sys
from typing import Optional, Any, Union, Dict, Tuple, cast

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from . import Addrfile
from . import configuration
from .exceptions import NotifierSetupError, ConfigError
from . import notifiers
from . import updaters


class DDNSManager:
    """Manages the rest of the Ruddr system. Creates notifiers and updaters and
    manages the addrfile.

    :param config: A :class:`~ruddr.Config` with the configuration to use

    :raises ConfigError: if configuration is not valid
    """

    def __init__(self, config: configuration.Config):
        self.log = logging.getLogger('ruddr')

        try:
            config.finalize(validate_notifier_type, validate_updater_type)
        except ConfigError as e:
            self.log.critical("Config error: %s", e)
            raise
        self.config = config

        #: Addrfile manager
        addrfile_name = os.path.join(self.config.main['datadir'], 'addrfile')
        self.addrfile = Addrfile(addrfile_name)

        # Creates self.notifiers and self.updaters as dicts
        self.notifiers: Dict[
            str, notifiers.BaseNotifier
        ] = self._create_notifiers()
        self.updaters: Dict[
            str, updaters.BaseUpdater
        ] = self._create_updaters()

        self._discard_unused_notifiers()

    def _create_notifiers(self) -> Dict[str, notifiers.BaseNotifier]:
        """Initialize the notifiers. Assumes the notifiers have been previously
        imported by :func:`validate_notifier_type`."""
        notifiers_dict: Dict[str, notifiers.BaseNotifier] = dict()
        for name, config in self.config.notifiers.items():
            module = config.get('module')
            notifier_type = config['type']

            if module is None:
                notifier_class = notifiers.notifiers[notifier_type]
            else:
                notifier_class = notifiers.notifiers[(module, notifier_type)]

            notifier = notifier_class(name, config)
            notifiers_dict[name] = notifier
        return notifiers_dict

    def _create_updaters(self) -> Dict[str, updaters.BaseUpdater]:
        """Initialize the updaters. Assumes the updaters have been previously
        imported by :func:`validate_updater_type`."""
        updater_dict: Dict[str, updaters.BaseUpdater] = dict()
        for name, config in self.config.updaters.items():
            module = config.get('module')
            updater_type = config['type']

            if module is None:
                updater_class = updaters.updaters[updater_type]
            else:
                updater_class = updaters.updaters[(module, updater_type)]

            updater = updater_class(name, self.addrfile, config)
            updater.initial_update()
            self._attach_updater_notifier(updater, config)
            updater_dict[name] = updater
        return updater_dict

    def _attach_updater_notifier(self, updater, config):
        """Attach the given :class:`~ruddr.Updater` to its notifier(s).
        Assumes config is valid; that is, notifiers all exist.

        :param updater: The :class:`~ruddr.Updater` to be attached
        :param config: That :class:`~ruddr.Updater`'s config
        """
        ipv4_notifier_name = config.get('notifier4')
        ipv6_notifier_name = config.get('notifier6')

        if ipv4_notifier_name is not None:
            ipv4_notifier = self.notifiers[ipv4_notifier_name]
            ipv4_notifier.attach_ipv4_updater(updater.update_ipv4)
        if ipv6_notifier_name is not None:
            ipv6_notifier = self.notifiers[ipv6_notifier_name]
            ipv6_notifier.attach_ipv6_updater(updater.update_ipv6)

    def _discard_unused_notifiers(self):
        """Remove notifiers that are not attached to an updater"""
        for name in list(self.notifiers.keys()):
            if not (self.notifiers[name].want_ipv4() or
                    self.notifiers[name].want_ipv6()):
                self.log.warning("Notifier %s not attached to any updater",
                                 name)
                del self.notifiers[name]

    def start(self):
        """Start running all notifiers. Returns after they start. The notifiers
        will continue running in background threads.

        :raises NotifierSetupError: if a notifier fails to start
        """
        self.log.info("Starting all notifiers...")

        for name, notifier in self.notifiers.items():
            try:
                notifier.start()
            except NotifierSetupError:
                self.log.critical("Notifier %s failed to start. Stopping all "
                                  "notifiers.", name)
                for running_notifier in self.notifiers.values():
                    running_notifier.stop()
                raise

        self.log.info("All notifiers started.")

    def do_notify(self):
        """Do an on-demand notify from all notifiers.

        Not all notifiers will support this, but most will.

        Does not raise any exceptions.
        """
        self.log.info("Checking once for all notifiers...")
        for notifier in self.notifiers.values():
            notifier.do_notify()
        self.log.info("Check for all notifiers complete.")

    def stop(self):
        """Stop all running notifiers gracefully. This will allow Python to
        exit naturally.

        Does not raise any exceptions, even if not yet started.
        """
        self.log.info("Stopping all notifiers...")
        for notifier in self.notifiers.values():
            notifier.stop()
        self.log.info("All notifiers stopped.")


def validate_notifier_type(module: Optional[str], type_: str) -> bool:
    """Check if a notifier type exists, importing it for :class:`DDNSManager`
    if it is not one of the built-in notifiers that comes with Ruddr

    :param module: ``None`` for built-in notifiers. Otherwise, the module the
                   notifier can be imported from.
    :param type_: The name of a built-in notifier or the class name of a
                  non-built-in notifier.
    :returns: ``True`` if the notifier exists, ``False`` otherwise
    """
    return _validate_updater_or_notifier_type(
        "notifier",
        notifiers.notifiers,
        module,
        type_
    )


def validate_updater_type(module: Optional[str], type_: str) -> bool:
    """Check if an updater type exists, importing it for :class:`DDNSManager`
    if it is not one of the built-in updaters that comes with Ruddr

    :param module: ``None`` for built-in updaters. Otherwise, the module the
                   updater can be imported from.
    :param type_: The name of a built-in updater or the class name of a
                  non-built-in updater.
    :returns: ``True`` if the updater exists, ``False`` otherwise
    """
    return _validate_updater_or_notifier_type(
        "updater",
        updaters.updaters,
        module,
        type_
    )


def _validate_updater_or_notifier_type(
    which: str,
    existing: Dict[Union[str, Tuple[str, str]], Any],
    module: Optional[str],
    type_: str,
) -> bool:
    """Check if an updater or notifier exists and import it

    :param which: ``"updater"`` or ``"notifier"``
    :param existing: The dict of already known updaters or notifiers and their
                     class. Keys are strings for built-in, (module, class) name
                     tuples for non-built-in
    :param module: ``None`` for built-in updaters or notifiers. Otherwise, the
                   module it can be imported from.
    :param type_: The name of a built-in updater or notifier or the class name
                  of a non-built-in one.
    :returns: ``True`` if the updater or notifier exists, ``False`` otherwise
    """
    if module is None:
        # Check if built-in or already imported with an entry point
        if type_ in existing:
            return True
        # Check if a ruddr entry point with this name exists
        discovered = entry_points(group=f"ruddr.{which}")
        try:
            entry_point = discovered[type_]
        except KeyError:
            return False
        existing[type_] = entry_point.load()
        return True

    # Check if already imported non-built-in
    if (module, type_) in existing:
        return True

    # Check if it's importable
    try:
        imported_module = importlib.import_module(module)
    except ImportError:
        return False
    try:
        imported_class = getattr(imported_module, type_)
    except AttributeError:
        return False
    existing[cast(Tuple[str, str], (module, type_))] = imported_class
    return True
