"""Ruddr notifier that listens for updates from systemd-networkd over DBus"""

#TODO add to setup.py for [systemd] requirements
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import ipaddress
import socket

from ..config import ConfigError
from ._get_iface_addrs import get_iface_addrs
from .notifier import SchedulerNotifier, Scheduled, NotifyError


class SystemdNotifier(SchedulerNotifier):
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

        # Max interval: Maximum number of seconds to go without checking the
        # current IP address, even without systemd-networkd signaling. It's not
        # clear if systemd-networkd signals in the event the IP address changes
        # but there was no other change in network connectivity (e.g. DHCP
        # server gives a different lease at renewal), so this ensures that any
        # such misses would not go undetected. This should be uncommon, if even
        # possible. Setting to 0 disables interval-based notifying.
        try:
            self.success_interval = int(config.get('max_interval', '21600'))
        except ValueError:
            self.log.critical("'max_interval' config option must be an "
                              "integer")
            raise ConfigError(f"'max_interval' option for {self.name} notifier"
                              " must be an integer") from None
        if self.success_interval < 0:
            self.success_interval = 0
        self.fail_min_interval = 60
        if self.success_interval > 0:
            if self.fail_max_interval > self.success_interval:
                self.fail_max_interval = self.success_interval
            if self.fail_min_interval > self.success_interval:
                self.fail_min_interval = self.success_interval

        # Allow private addresses: By default, addresses in private IP space
        # (192.168.0.0/16, 10.0.0.0/8, 192.0.2.0/24, fc00::/7, 2001:db8::/32,
        # etc.) are ignored when assigned to the monitored interface. If this
        # is set to 'true', 'on', or 'yes' (case insensitive), these addresses
        # will be eligible to be picked up and sent to the notifier.
        # Non-private addresses will still take precedence, and link-local
        # addresses are always ignored.
        self.allow_private = config.get('allow_private', 'no')
        if self.allow_private.lower() in ('yes', 'true', 'on'):
            self.allow_private = True
        else:
            self.allow_private = False

    def check_once(self):
        self.log.info("Checking IP addresses.")

        try:
            omit_private = not self.allow_private
            ipv4s, ipv6s = get_iface_addrs(self.iface, omit_private)
        except ValueError:
            self.log.error("Interface %s does not exist", self.iface)
            raise NotifyError("Interface %s does not exist" %
                              self.iface) from None
        except NotImplementedError as e:
            self.log.error(str(e))
            raise NotifyError("Could not look up address") from e

        ipv4_addressed = True
        ipv6_addressed = True
        if self.need_ipv4():
            try:
                ipv4 = ipv4s[0]
            except IndexError:
                self.log.warning("Interface %s has no IPv4 assigned",
                                 self.iface)
                ipv4_addressed = False
            else:
                self.notify_ipv4(ipv4)

        if self.need_ipv6():
            try:
                ipv6 = ipv6s[0]
            except IndexError:
                self.log.warning("Interface %s has no IPv6 assigned",
                                 self.iface)
                ipv6_addressed = False
            else:
                ipv6 = ipaddress.IPv6Interface(
                    (ipv6, self.ipv6_prefix)).network
                self.notify_ipv6(ipv6)

        if not ipv4_addressed:
            raise NotifyError("Interface %s has no IPv4 assigned" %
                              self.iface) from None
        if not ipv6_addressed:
            raise NotifyError("Interface %s has no IPv6 assigned" %
                              self.iface) from None

    @Scheduled
    def _check_and_notify(self):
        """Check the current address of the selected interface and notify.
        Does the same thing as :meth:`check_once`, but with retries and
        automatically schedules the next check."""
        self.check_once()

    def _handle_dbus_signal(self, type_, changed, invalidated, path):
        """Handle a PropertiesChanged DBus signal.

        :param type_: Type whose properties changed
        :param changed: Dict of the changed property names and new values
        :param invalidated: List of changed property names without values (this
                            should not be necessary for
                            :class:`SystemdNotifier`'s purposes.
        :param path: Path to the object whose properties changed
        """
        self.log.debug("Received signal: type=%r, changed=%r, invalidated=%r, "
                       "path=%r", type_, changed, invalidated, path)
        if type_ != 'org.freedesktop.network1.Link':
            self.log.debug("Ignoring signal for type we don't care about.")
            return
        if not path.startswith('/org/freedesktop/network1/link/_3'):
            self.log.debug("Unexpected path for org.freedesktop.network1.Link "
                           "object: %s Ignoring signal.", path)
            return

        # Extract interface index and lookup name
        _, _, iface_idx = path.rpartition('/')
        iface_idx = int(iface_idx[2:])
        try:
            iface_name = socket.if_indextoname(iface_index)
        except OSError as e:
            self.log.warning("Received updates for interface index %d but "
                             "cannot lookup interface name, so skipping: %s",
                             iface_idx, e)
            return

        # Check if interface is one we care about, check address and send
        # update if so
        if iface_name == self.iface:
            self._check_and_notify()

    def _setup_dbus(self):
        """Subscribe to the system DBus, register signal handlers, and start
        main loop. Should be run in a separate thread."""
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        bus = dbus.SystemBus()
        bus.add_signal_receiver(self._handle_dbus_signal,
                                bus_name='org.freedesktop.network1',
                                signal_name='PropertiesChanged',
                                path_keyword='path')
        self.log.debug("Subscribed to org.freedesktop.network1")

        mainloop = glib.MainLoop()
        mainloop.run()


    def setup(self):
        """Do any initial setup only necessary for daemon mode, such as
        subscribing to a message queue. Errors here are considered fatal.

        For this class, subscribe to the system DBus.
        """

        #TODO Glib mainloop thingy and imports for it
