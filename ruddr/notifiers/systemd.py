"""Ruddr notifier that listens for updates from systemd-networkd over DBus"""
import threading

from gi.repository import GLib
from gi.repository import Gio
import ipaddress
import socket

from ruddr.exceptions import NotifyError, NotifierSetupError, ConfigError
from ._getifaceaddrs import get_iface_addrs
from .notifier import Notifier


class SystemdNotifier(Notifier):
    """Ruddr notifier that listens for updates from systemd-networkd over DBus
    """

    def __init__(self, name, config):
        super().__init__(name, config)

        # Interface to get address from. Normally, both IPv4 and IPv6 addresses
        # are checked. If only IPv4 is needed, use "notifier4=" to attach this
        # notifier to updaters in the config instead of plain "notifier=". If
        # there are no updaters requesting IPv6 addresses from this notifier,
        # it will skip checking the IPv6 address on the interface. (Vice versa
        # for skipping IPv4.)
        try:
            self.iface = config['iface']
        except KeyError:
            self.log.critical("'iface' config option is required")
            raise ConfigError(f"{self.name} notifier requires 'iface' config "
                              "option") from None

        # IPv6 prefix: Number of bits in the network prefix. Defaults to 64,
        # but can be manually specified in case your ISP delegates a shorter
        # prefix.
        try:
            self.ipv6_prefix = int(config.get('ipv6_prefix', '64'))
        except ValueError:
            self.log.critical("'ipv6_prefix' config option must be an integer "
                              "from 1-128")
            raise ConfigError(f"'ipv6_prefix' option for {self.name} notifier "
                              "must be an integer from 1-128") from None
        if not (1 <= self.ipv6_prefix <= 128):
            self.log.critical("'ipv6_prefix' config option must be an integer "
                              "from 1-128")
            raise ConfigError(f"'ipv6_prefix' option for {self.name} notifier "
                              "must be an integer from 1-128")

        # Allow private addresses: By default, addresses in private IP space
        # (192.168.0.0/16, 10.0.0.0/8, 192.0.2.0/24, fc00::/7, 2001:db8::/32,
        # etc.) are ignored when assigned to the monitored interface. If this
        # is set to 'true', 'on', or 'yes' (case insensitive), these addresses
        # will be eligible to be picked up and sent to the notifier.
        # Non-private addresses will still take precedence, and link-local
        # addresses are always ignored.
        self.allow_private = config.get('allow_private', 'no')
        if self.allow_private.lower() in ('yes', 'true', 'on', '1'):
            self.allow_private = True
        else:
            self.allow_private = False

        # It's not clear if systemd-networkd signals in the event the IP
        # IP address changes but there was no other change in network
        # connectivity (e.g. DHCP server gives a different lease at renewal).
        # So, we also check the IP address on a schedule by default just in
        # case (though this should be uncommon, if even possible). If we want
        # to disable this, just set the success interval to 0.
        self.set_check_intervals(retry_min_interval=60,
                                 retry_max_interval=21600,
                                 success_interval=21600,
                                 config=config)

        # Will store a reference to the GLib main loop, so we can stop it later
        self.mainloop = None

    def check_once(self):
        self.log.info("Checking IP addresses.")

        # Look up the interface and get the current assigned addresses
        try:
            omit_private = not self.allow_private
            ipv4s, ipv6s = get_iface_addrs(self.iface, omit_private)
        except ValueError:
            self.log.error("Interface %s does not exist", self.iface)
            raise NotifyError("Interface %s does not exist" %
                              self.iface) from None

        # None if not wanted, otherwise True if assigned, False if not assigned
        got_ipv4 = None
        got_ipv6 = None

        if self.want_ipv4():
            try:
                ipv4 = ipv4s[0]
            except IndexError:
                got_ipv4 = False
                self.log.info("Interface %s has no IPv4 assigned",
                              self.iface)
            else:
                got_ipv4 = True
                self.notify_ipv4(ipv4)

        if self.want_ipv6():
            try:
                ipv6 = ipv6s[0]
            except IndexError:
                got_ipv6 = False
                self.log.info("Interface %s has no IPv6 assigned",
                              self.iface)
            else:
                ipv6 = ipaddress.IPv6Interface(
                    (ipv6, self.ipv6_prefix)).network
                got_ipv6 = True
                self.notify_ipv6(ipv6)

        # Error if no wanted address was found
        if not (got_ipv4 or got_ipv6):
            raise NotifyError("Interface %s has no address assigned" %
                              self.iface)

        # Error for any missing wanted and needed addresses
        if self.need_ipv4() and not got_ipv4:
            raise NotifyError("Interface %s has no IPv4 assigned" %
                              self.iface)
        if self.need_ipv6() and not got_ipv6:
            raise NotifyError("Interface %s has no IPv6 assigned" %
                              self.iface)

    def _handle_network_change(self, iface_idx, changed, invalidated):
        """Act on a PropertiesChanged signal for a network interface by
        checking if it's the interface we care about, then checking for the
        current IP address and notifying if so.

        :param iface_idx: Index of the interface whose properties changed
        :param changed: Dict of the changed property names and new values
        :param invalidated: List of changed property names without values (this
                            should not be necessary for
                            :class:`SystemdNotifier`'s purposes).
        """

        # In an ideal world, we would want to inspect the changed properties
        # to determine whether we should expect a valid address. However,
        # org.freedesktop.network1 isn't documented at all as of Sep. 28, 2021
        # (apart from what can be determined from introspection; see:
        # busctl introspect org.freedesktop.network1 /org/freedesktop/network1
        # and also introspect on individual links).
        #
        # At first glance, it seemed "man networkctl" could provide info on
        # what the state properties mean, but there doesn't seem to be a
        # perfect correspondence between networkctl's output and the state
        # properties on DBus.
        #
        # TODO Look into this more in the future. Maybe it will be better
        # documented.

        # Look up interface name
        try:
            iface_name = socket.if_indextoname(iface_idx)
        except OSError as e:
            self.log.warning("Received updates for interface index %d but "
                             "cannot lookup interface name, so skipping: %s",
                             iface_idx, e)
            return

        # Check if interface is the one we care about, check address and send
        # update if so
        if iface_name == self.iface:
            self.check()

    def _handle_properties_changed(self, connection, sender_name, object_path,
                                   interface_name, signal_name, parameters,
                                   user_data):
        """Handle a PropertiesChanged signal. Do nothing if it's not on a type
        we care about (org.freedesktop.network1.link). Otherwise, extract the
        useful info and start a potential notify.

        :param connection: :class:`gi.repository.Gio.DBusConnection` object
        :param sender_name: Bus name of the signal's sender
        :param object_path: Object path the signal was emitted on
        :param interface_name: Name of the signal's interface
        :param signal_name: Name of the signal
        :param parameters: :class:`gi.repository.GLib.Variant` tuple with the
                           signal's parameters
        :param user_data: User data provided when subscribing to the signal

        See https://lazka.github.io/pgi-docs/Gio-2.0/callbacks.html#Gio.DBusSignalCallback
        """
        # Extract parameters from GLib.Variant
        type_, changed, invalidated = parameters.unpack()
        self.log.debug("Received signal: type=%r, changed=%r, invalidated=%r, "
                       "path=%r", type_, changed, invalidated, object_path)

        # Check if we care about this property change
        if type_ != 'org.freedesktop.network1.Link':
            self.log.debug("Ignoring signal for type we don't care about.")
            return
        if not object_path.startswith('/org/freedesktop/network1/link/_3'):
            self.log.debug("Unexpected path for org.freedesktop.network1.Link "
                           "object: %s Ignoring signal.", object_path)
            return
        pass

        # Extract interface index from signal path: DBus names cannot start
        # with a numeral. Since interface indices do, systemd substitutes
        # "_xx" for the first digit, where "xx" is the codepoint for that
        # character. E.g. index 12 would be .../_312 since "1" is ASCII 0x31.
        # Conveniently, the digits 0-9 are 0x30-0x39, so we can just chop off
        # the "_3".
        _, _, iface_idx = object_path.rpartition('/')
        iface_idx = int(iface_idx[2:])

        self._handle_network_change(iface_idx, changed, invalidated)

    def _dbus_listen(self):
        """Subscribe to the system DBus and register signal handlers. Does not
        return until the main loop is quit."""
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        except GLib.Error:
            bus = None
        if bus is None:
            self.log.critical("Could not connect to system DBus")
            raise NotifierSetupError("Notifier %s could not connect to system "
                                     "dbus" % self.name)
        else:
            self.log.debug("Connected to system DBus")

        bus.signal_subscribe('org.freedesktop.network1',
                             'org.freedesktop.DBus.Properties',
                             'PropertiesChanged',
                             None,
                             None,
                             Gio.DBusSignalFlags.NONE,
                             self._handle_properties_changed,
                             None)
        self.log.debug("Subscribed to PropertiesChanged DBus signal")

        self.mainloop = GLib.MainLoop()
        self.log.debug("Starting main loop")
        self.mainloop.run()
        self.log.debug("Main loop stopped.")

    def setup(self):
        # Start monitoring DBus
        self.log.debug("Starting to monitor DBus.")
        thread = threading.Thread(target=self._dbus_listen)
        thread.start()

    def teardown(self):
        # Stop monitoring DBus
        if self.mainloop is None:
            self.log.debug("Main loop not started, nothing to stop")
        else:
            self.log.debug("Stopping main loop...")
            self.mainloop.quit()
