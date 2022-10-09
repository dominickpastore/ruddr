"""DDNS Manager: Initializes notifiers and updaters and manages the addrfile"""

import argparse
import importlib
import ipaddress
import json
import logging
import logging.handlers
import signal
import sys
import time
from typing import Optional, Any, Union, Dict

from . import configuration
from .exceptions import RuddrException, NotifierSetupError, ConfigError
from . import notifiers
from . import sdnotify
from . import updaters


log = logging.getLogger('ruddr')


class _IPJSONEncoder(json.JSONEncoder):
    """Subclass of JSONDecoder that can handle IPv4Address and IPv6Network"""
    def default(self, o):
        if isinstance(o, ipaddress.IPv4Address):
            return o.exploded
        elif isinstance(o, ipaddress.IPv6Network):
            return o.compressed
        return super().default(o)


def _decode_ips(d):
    """Object hook that decodes IP addresses. Raises a ValueError if the value
    of an 'ipv4' key cannot be converted to an IPv4Address or the value of an
    'ipv6' key cannot be converted to an IPv6Address."""
    if 'ipv4' in d and d['ipv4'] is not None:
        try:
            d['ipv4'] = ipaddress.IPv4Address(d['ipv4'])
        except ValueError as e:
            log.warning("Malformed IPv4 in addrfile: %s. Ignoring.", e)
            d['ipv4'] = None
    if 'ipv6' in d and d['ipv6'] is not None:
        try:
            d['ipv6'] = ipaddress.IPv6Interface(d['ipv6']).network
        except ValueError as e:
            log.warning("Malformed IPv6 network in addrfile: %s. Ignoring.", e)
            d['ipv6'] = None
    return d


class DDNSManager:
    """Manages the rest of the Ruddr system. Creates notifiers and updaters and
    manages the addrfile.

    :param config: A :class:`~ruddr.ConfigReader` with the configuration to
                   use
    """

    def __init__(self, config):
        self.config = config

        #: Addrfile path
        self.addrfile = self.config.main['addrfile']

        #: Addrfile data. Stores contents of addrfile between writes.
        self.addresses = dict()
        self._read_addrfile()

        # Creates self.notifiers and self.updaters as dicts
        self._create_notifiers()
        self._create_updaters()

        self._discard_unused_notifiers()

    def _create_notifiers(self):
        """Initialize the notifiers. Assumes the notifiers have been previously
        imported by :func:`validate_notifier_type`."""
        self.notifiers = dict()
        for name, config in self.config.notifiers.items():
            module = config.get('module')
            notifier_type = config['type']

            if module is None:
                notifier_class = notifiers.notifiers[notifier_type]
            else:
                notifier_class = notifiers.notifiers[(module, notifier_type)]

            notifier = notifier_class(name, config)
            self.notifiers[name] = notifier

    def _create_updaters(self):
        """Initialize the updaters. Assumes the updaters have been previously
        imported by :func:`validate_updater_type`."""
        self.updaters = dict()
        for name, config in self.config.updaters.items():
            module = config.get('module')
            updater_type = config['type']

            if module is None:
                updater_class = updaters.updaters[updater_type]
            else:
                updater_class = updaters.updaters[(module, updater_type)]

            updater = updater_class(name, self, config)
            self._attach_updater_notifier(updater, config)
            self.updaters[name] = updater

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
                del self.notifiers[name]

    def start(self):
        """Start running all notifiers.

        :raises NotifierSetupError: when a notifier fails to start.
        """
        log.info("Starting all notifiers...")

        for name, notifier in self.notifiers.items():
            try:
                notifier.start()
            except NotifierSetupError:
                log.error("Notifier %s failed to start. Stopping all "
                          "notifiers.", name)
                for running_notifier in self.notifiers.values():
                    running_notifier.stop()
                raise

        log.info("All notifiers started.")

    def check_once(self):
        """Do a single notify from all notifiers.

        :raises NotifyError: if any notifier fails to notify.
        """
        log.info("Checking once for all notifiers...")

        exc = None
        for name, notifier in self.notifiers.items():
            try:
                notifier.check_once()
            except NotifierSetupError as e:
                log.error("Notifier %s failed to check.",
                          name, exc_info=True)
                if exc is None:
                    exc = e
        if exc is not None:
            raise exc

        log.info("Check for all notifiers complete.")

    def stop(self):
        """Stop all running notifiers."""
        log.info("Stopping all notifiers...")
        for notifier in self.notifiers.values():
            notifier.stop()
        log.info("All notifiers stopped.")

    def _read_addrfile(self):
        """Read the addrfile in. If it cannot be read or is malformed, log and
        return without touching :attr:`self.addresses`."""
        try:
            with open(self.addrfile, 'r') as f:
                addresses = json.load(f, object_hook=_decode_ips)
        except json.JSONDecodeError as e:
            log.warning("Malformed JSON in addrfile %s at (%d:%d). Will "
                        "recreate.", self.addrfile, e.lineno, e.colno)
            return
        except OSError as e:
            log.warning("Could not read addrfile %s (%s). Will attempt to "
                        "recreate.", self.addrfile, e.strerror)
            return
        if not isinstance(addresses, dict):
            log.warning("Addrfile %s has unexpected JSON structure. Will "
                        "recreate.", self.addrfile)
            return

        # Check that each key contains a properly formed dict (only keys ipv4
        # and ipv6, values are None or appropriate type of address)
        for name, addrs in list(addresses.items()):
            if not isinstance(addrs, dict):
                log.warning("Addrfile %s has unexpected JSON structure for "
                            "key %s. Will recreate that key.",
                            self.addrfile, name)
                addresses[name] = {'ipv4': None, 'ipv6': None}
                continue
            key_count = 0
            if 'ipv4' in addrs:
                key_count += 1
                if not (addrs['ipv4'] is None or
                        isinstance(addrs['ipv4'], ipaddress.IPv4Address)):
                    log.warning("Addrfile %s has unexpected JSON structure "
                                "for key %s. Will recreate that key.",
                                self.addrfile, name)
                    addresses[name] = {'ipv4': None, 'ipv6': None}
                    continue
            if 'ipv6' in addrs:
                key_count += 1
                if not (addrs['ipv6'] is None or
                        isinstance(addrs['ipv6'], ipaddress.IPv6Network)):
                    log.warning("Addrfile %s has unexpected JSON structure "
                                "for key %s. Will recreate that key.",
                                self.addrfile, name)
                    addresses[name] = {'ipv4': None, 'ipv6': None}
                    continue
            if len(addrs) > key_count:
                log.warning("Addrfile %s has unexpected JSON structure for "
                            "key %s. Will recreate that key.",
                            self.addrfile, name)
                addresses[name] = {'ipv4': None, 'ipv6': None}

        self.addresses = addresses

    def _write_addrfile(self):
        """Write out the addrfile. If it cannot be written, log the error but
        do not raise an exception."""
        try:
            with open(self.addrfile, 'w') as f:
                json.dump(self.addresses, f, cls=_IPJSONEncoder,
                          sort_keys=True, indent=4)
        except OSError as e:
            log.error("Could not write addrfile %s: %s",
                      self.addrfile, e.strerror)

    def addrfile_get_ipv4(self, name):
        """Get the IPv4 entry from the addrfile for the named updater.

        If the file could not be opened, there was no entry for the named
        updater, or the addrfile or entry were malformed, returns None.

        :param name: Name of the updater to fetch the address for
        :return: An :class:`IPv4Address` or None
        """
        try:
            addrs = self.addresses[name]
        except KeyError:
            addrs = {'ipv4': None, 'ipv6': None}
            self.addresses[name] = addrs

        try:
            return addrs['ipv4']
        except KeyError:
            self.addresses[name]['ipv4'] = None
            return None

    def addrfile_get_ipv6(self, name):
        """Get the IPv6 entry from the addrfile for the named updater.

        If the file could not be opened, there was no entry for the named
        updater, or the addrfile or entry were malformed, returns None.

        :param name: Name of the updater to fetch the address for
        :return: An :class:`IPv6Network` or None
        """
        try:
            addrs = self.addresses[name]
        except KeyError:
            addrs = {'ipv4': None, 'ipv6': None}
            self.addresses[name] = addrs

        try:
            return addrs['ipv6']
        except KeyError:
            self.addresses[name]['ipv6'] = None
            return None

    def addrfile_set_ipv4(self, name, addr):
        """Set the IPv4 entry for the named updater in the addrfile.

        If the file could not be written, the error is logged but no exception
        is raised.

        :param name: Name of the updater to write the address for
        :param addr: An :class:`IPv4Address` to write
        """
        if name in self.addresses:
            self.addresses[name]['ipv4'] = addr
        else:
            self.addresses[name] = {'ipv4': addr, 'ipv6': None}

        self._write_addrfile()

    def addrfile_set_ipv6(self, name, addr):
        """Set the IPv6 entry for the named updater in the addrfile.

        If the file could not be written, the error is logged but no exception
        is raised.

        :param name: Name of the updater to write the address for
        :param addr: An :class:`IPv6Network` to write
        """
        if name in self.addresses:
            self.addresses[name]['ipv6'] = addr
        else:
            self.addresses[name] = {'ipv4': None, 'ipv6': addr}

        self._write_addrfile()


def parse_args(argv):
    """Parse command line arguments

    :param argv: Either ``None`` or a list of arguments
    :returns: a :class:`argparse.Namespace` containing the parsed arguments
    """
    parser = argparse.ArgumentParser(description="Robotic Updater for "
                                     "Dynamic DNS Records")
    parser.add_argument("-1", "--check-once", action="store_true",
                        help="Check and update all IP addresses a single time")
    parser.add_argument("-c", "--configfile", default="/etc/ruddr.conf",
                        help="Path to the config file")
    parser.add_argument("-d", "--debug-logs", action="store_true",
                        help="Increase verbosity of logging significantly")
    parser.add_argument("-s", "--stderr", action="store_true",
                        help="Log to stderr instead of syslog or file")
    return parser.parse_args(argv)


def validate_notifier_type(module: Optional[str], type_: str) -> bool:
    """Check if an notifier type exists, importing it for :class:`DDNSManager`
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
    existing: Dict[Union[str, (str, str)], Any],
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
        # TODO Check ruddr.notifiers or ruddr.updaters entry points
        return False

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
    existing[(module, type_)] = imported_class
    return True


def main(argv=None):
    """Main entry point when run as a standalone program"""
    args = parse_args(argv)
    conf_reader = configuration.ConfigReader(validate_notifier_type,
                                             validate_updater_type)
    try:
        conf = conf_reader.read_file_path(args.configfile)
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
    manager = DDNSManager(conf)
    if args.check_once:
        try:
            manager.check_once()
        except RuddrException:
            sys.exit(1)
        return
    try:
        manager.start()
    except RuddrException:
        # Exception happened, but generated within Ruddr, so it should be
        # sufficiently logged. Just exit.
        sys.exit(1)
    except:
        log.critical("Uncaught exception!", exc_info=True)
        sys.exit(1)

    # Notify systemd, if applicable
    sdnotify.ready()

    # Wait for SIGINT (^C) or SIGTERM
    def handle_signals(sig, frame):
        log.info("Received signal:", signal.strsignal(sig))
        sdnotify.stopping()
        manager.stop()
    signal.signal(signal.SIGINT, handle_signals)
    signal.signal(signal.SIGTERM, handle_signals)
    while True:
        time.sleep(60)


if __name__ == '__main__':
    main()
