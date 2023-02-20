"""DDNS Manager: Initializes notifiers and updaters and manages the addrfile"""

import argparse
import importlib
import logging
import logging.handlers
import os.path
import signal
import sys
from typing import Optional, Any, Union, Dict, Tuple, cast

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from . import Addrfile
from . import configuration
from .exceptions import NotifierSetupError, ConfigError, RuddrSetupError
from . import notifiers
from ruddr.util import sdnotify
from . import updaters


log = logging.getLogger('ruddr')


class DDNSManager:
    """Manages the rest of the Ruddr system. Creates notifiers and updaters and
    manages the addrfile.

    :param config: A :class:`~ruddr.Config` with the configuration to use

    :raises ConfigError: if configuration is not valid
    """

    def __init__(self, config: configuration.Config):
        try:
            config.finalize(validate_notifier_type, validate_updater_type)
        except ConfigError as e:
            log.critical("Config error: %s", e)
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
                log.warning("Notifier %s not attached to any updater", name)
                del self.notifiers[name]

    def start(self):
        """Start running all notifiers. Returns after they start. The notifiers
        will continue running in background threads.

        :raises NotifierSetupError: if a notifier fails to start
        """
        log.info("Starting all notifiers...")

        for name, notifier in self.notifiers.items():
            try:
                notifier.start()
            except NotifierSetupError:
                log.critical("Notifier %s failed to start. Stopping all "
                             "notifiers.", name)
                for running_notifier in self.notifiers.values():
                    running_notifier.stop()
                raise

        log.info("All notifiers started.")

    def do_notify(self):
        """Do an on-demand notify from all notifiers.

        Not all notifiers will support this, but most will.

        Does not raise any exceptions.
        """
        log.info("Checking once for all notifiers...")
        for notifier in self.notifiers.values():
            notifier.do_notify()
        log.info("Check for all notifiers complete.")

    def stop(self):
        """Stop all running notifiers gracefully. This will allow Python to
        exit naturally.

        Does not raise any exceptions, even if not yet started.
        """
        log.info("Stopping all notifiers...")
        for notifier in self.notifiers.values():
            notifier.stop()
        log.info("All notifiers stopped.")


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


def parse_args(argv):
    """Parse command line arguments

    :param argv: Either ``None`` or a list of arguments
    :returns: a :class:`argparse.Namespace` containing the parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Robotic Updater for Dynamic DNS Records",
        epilog="SIGUSR1 will cause a running instance to immediately check and"
               " update the current IP address(es) if possible",
    )
    parser.add_argument("-c", "--configfile", default="/etc/ruddr.conf",
                        help="Path to the config file")
    parser.add_argument("-d", "--debug-logs", action="store_true",
                        help="Increase verbosity of logging significantly")
    parser.add_argument("-s", "--stderr", action="store_true",
                        help="Log to stderr instead of syslog or file")
    return parser.parse_args(argv)


def main(argv=None):
    """Main entry point when run as a standalone program"""
    args = parse_args(argv)
    try:
        conf = configuration.read_config_from_path(args.configfile)
    except ConfigError as e:
        print("Config error:", e, file=sys.stderr)
        sys.exit(2)

    # Set up logging handler
    if args.stderr:
        logfile = 'stderr'
    else:
        logfile = conf.main.get('log', 'syslog')
    if logfile == 'syslog':
        log_handler = logging.handlers.SysLogHandler()
    elif logfile == 'stderr':
        log_handler = logging.StreamHandler()
    else:
        log_handler = logging.FileHandler(logfile)
    log.addHandler(log_handler)
    if args.debug_logs:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    # Start up the actual DDNS code
    try:
        manager = DDNSManager(conf)
        manager.start()
    except RuddrSetupError:
        log.critical("Ruddr failed to start.")
        sys.exit(1)

    # Notify systemd, if applicable
    sdnotify.ready()

    # Do an immediate update on SIGUSR1
    def handle_sigusr1(sig, _):
        log.info("Received signal: %s", signal.Signals(sig).name)
        manager.do_notify()
    signal.signal(signal.SIGUSR1, handle_sigusr1)

    # Wait for SIGINT (^C) or SIGTERM
    def handle_signals(sig, _):
        log.info("Received signal: %s", signal.Signals(sig).name)
        sdnotify.stopping()
        manager.stop()
    signal.signal(signal.SIGINT, handle_signals)
    signal.signal(signal.SIGTERM, handle_signals)

    # TODO Do we need this? If not, remove it
    # while True:
    #     time.sleep(60)


if __name__ == '__main__':
    main()
