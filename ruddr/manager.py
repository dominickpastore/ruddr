"""DDNS Manager: Initializes notifiers and updaters and manages the addrfile"""

import importlib
import ipaddress
import json

import config
import notifiers
import updaters


class RuddrException(Exception):
    """Base class for all Ruddr exceptions except PublishError, which is never
    raised by Ruddr."""
    #TODO Main entry point should have handlers for all RuddrException that
    # logs the error and then exits


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
    if 'ipv4' in d:
        if d['ipv4'] is not None:
            try:
                d['ipv4'] = ipaddress.IPv4Address(d['ipv4'])
            except ValueError:
                logging.warning("Malformed IPv4 in addrfile: %s. Ignoring.",
                                self.addrfile, e)
                d['ipv4'] = None
    if 'ipv6' in d:
        if d['ipv6'] is not None:
            try:
                d['ipv6'] = ipaddress.IPv6Interface(d['ipv6']).network
            except ValueError:
                logging.warning("Malformed IPv6 network in addrfile: %s. "
                                "Ignoring.", self.addrfile, e)
                d['ipv6'] = None
    return d


class DDNSManager:
    """Manages the rest of the Ruddr system. Creates notifiers and updaters and
    manages the addrfile.

    :param configfile: Path to the configuration file
    """

    def __init__(self, configfile='/etc/ruddr.conf'):
        self.config = config.ConfigReader(configfile)

        #: Addrfile path
        self.addrfile = self.config.main['addrfile']

        #: Addrfile data. Stores contents of addrfile between writes.
        self.addresses = dict()
        self._read_addrfile()

        # Creates self.notifiers and self.updaters as dicts
        self._create_notifiers()
        self._create_updaters()

        #TODO Make notifiers start

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

    def get_notifier(self, name):
        """Retrieve a notifier by name.

        :raises KeyError: if the notifier does not exist.
        """
        return self.notifiers[name]

    def _read_addrfile(self):
        """Read the addrfile in. If it cannot be read or is malformed, log and
        return without touching :attr:`self.addresses`."""
        try:
            with open(self.addrfile, 'r') as f:
                addresses = json.load(f, object_hook=_decode_ips)
        except json.JSONDecodeError as e:
            logging.warning("Malformed JSON in addrfile %s at (%d:%d). Will "
                            "recreate.", self.addrfile, e.lineno, e.colno)
            return
        except OSError as e:
            logging.warning("Could not read addrfile %s (%s). Will attempt to "
                            "recreate.", self.addrfile, e.strerror)
            return
        if not isinstance(self.addrs, dict):
            logging.warning("Addrfile %s has unexpected JSON structure. Will "
                            "recreate.", self.addrfile)
            return

        # Check that each key contains a properly formed dict (only keys ipv4
        # and ipv6, values are None or appropriate type of address)
        for name, addrs in list(addresses.items()):
            if not isinstance(addrs, dict):
                logging.warning("Addrfile %s has unexpected JSON structure for"
                                " key %s. Will recreate that key.",
                                self.addrfile, name)
                addresses[name] = {'ipv4': None, 'ipv6': None}
                continue
            key_count = 0
            if 'ipv4' in addrs:
                key_count += 1
                if not (addrs['ipv4'] is None or
                        isinstance(addrs['ipv4'], ipaddress.IPv4Address)):
                    logging.warning("Addrfile %s has unexpected JSON structure"
                                    " for key %s. Will recreate that key.",
                                    self.addrfile, name)
                    addresses[name] = {'ipv4': None, 'ipv6': None}
                    continue
            if 'ipv6' in addrs:
                key_count += 1
                if not (addrs['ipv6'] is None or
                        isinstance(addrs['ipv6'], ipaddress.IPv6Network)):
                    logging.warning("Addrfile %s has unexpected JSON structure"
                                    " for key %s. Will recreate that key.",
                                    self.addrfile, name)
                    addresses[name] = {'ipv4': None, 'ipv6': None}
                    continue
            if len(addrs) > key_count:
                logging.warning("Addrfile %s has unexpected JSON structure for"
                                " key %s. Will recreate that key.",
                                self.addrfile, name)
                addresses[name] = {'ipv4': None, 'ipv6': None}

        self.addresses = addresses

    def _write_addrfile(self):
        """Write out the addrfile. If it cannot be written, log the error but
        do not raise an exception."""
        try:
            with open(self.addrfile, 'w') as f:
                json.dump(f, self.addresses, cls=IPJSONEncoder,
                          sort_keys=True, indent=4)
        except OSError as e:
            logging.error("Could not write addrfile %s: %s",
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
