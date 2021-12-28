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

from . import config
from .exceptions import RuddrException, NotifierSetupError
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
        """Initialize the notifiers"""
        self.notifiers = dict()
        for name, config in self.config.notifiers.items():
            module = config.get('module')
            try:
                notifier_type = config['type']
            except KeyError:
                raise config.ConfigError("Notifier %s requires a type"
                                         % name) from None

            if module is None:
                try:
                    notifier_class = notifiers.notifiers[notifier_type]
                except KeyError:
                    #TODO Use ruddr.notifiers entry points
                    raise config.ConfigError("No built-in notifier of type %s"
                                             % notifier_type) from None
            else:
                try:
                    imported = importlib.import_module(module)
                except ImportError:
                    raise config.ConfigError("Notifier module %s cannot be "
                                             "imported" % module) from None
                try:
                    notifier_class = getattr(imported, notifier_type)
                except AttributeError:
                    raise config.ConfigError(
                        "Notifier module %s has not class %s" %
                        (module, notifier_type)) from None

            notifier = notifier_class(name, config)
            self.notifiers[name] = notifier

    def _create_updaters(self):
        """Initialize the updaters

        :raises ConfigError: when updater type is not provided, does not exist,
                             or custom updater module cannot be imported
        """
        self.updaters = dict()
        for name, config in self.config.updaters.items():
            module = config.get('module')
            try:
                updater_type = config['type']
            except KeyError:
                raise config.ConfigError("Updater %s requires a type" % name) \
                    from None

            if module is None:
                try:
                    updater_class = updaters.updaters[updater_type]
                except KeyError:
                    #TODO Use ruddr.updaters entry points
                    raise config.ConfigError("No built-in updater of type %s" %
                                             updater_type) from None
            else:
                try:
                    imported = importlib.import_module(module)
                except ImportError:
                    raise config.ConfigError("Updater module %s cannot be "
                                             "imported" % module) from None
                try:
                    updater_class = getattr(imported, updater_type)
                except AttributeError:
                    raise config.ConfigError(
                        "Updater module %s has not class %s" %
                        (module, updater_type)) from None

            updater = updater_class(name, self, self.config.main, config)
            self.updaters[name] = updater

    def _discard_unused_notifiers(self):
        """Remove notifiers that are not attached to an updater"""
        for name in list(self.notifiers.keys()):
            if not (self.notifiers[name].want_ipv4() or
                    self.notifiers[name].want_ipv6()):
                del self.notifiers[name]

    def get_notifier(self, name):
        """Retrieve a notifier by name.

        :raises KeyError: if the notifier does not exist.
        """
        return self.notifiers[name]

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
                for notifier in self.notifiers.values():
                    notifier.stop()
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


def main(argv=None):
    """Main entry point when run as a standalone program"""
    args = parse_args(argv)
    conf = config.ConfigReader(args.configfile)

    # Set up logging handler
    if args.stderr:
        logfile = 'stderr'
    else:
        logfile = conf.main.get('log', 'syslog')
    if logfile == 'syslog':
        log_handler = logging.handlers.SysLogHandler()
    if logfile == 'stderr':
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
