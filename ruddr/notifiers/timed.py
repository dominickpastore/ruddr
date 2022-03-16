"""Ruddr notifier that checks the IP address of a local interface on a
schedule"""

import ipaddress

from ..exceptions import NotifyError, ConfigError
from ._getifaceaddrs import get_iface_addrs
from .notifier import ScheduledNotifier


class TimedNotifier(ScheduledNotifier):
    """Ruddr notifier that checks the IP address of a local interface on a
    schedule"""

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

        # Check interval: Number of seconds between successful IP address
        # checks
        try:
            self.success_interval = int(config.get('interval', '1800'))
        except ValueError:
            self.log.critical("'interval' config option must be an integer")
            raise ConfigError(f"'interval' option for {self.name} notifier"
                              " must be an integer") from None
        if self.success_interval < 0:
            self.success_interval = 0

        # Retry min and max interval: Number of seconds to wait before retrying
        # after a failed IP address check (e.g. the interface hasn't obtained
        # an IP # address yet or a cable is unplugged). When a check first
        # fails, the min interval is used, but the retry interval grows after
        # each failure until the max interval is reached. After a successful
        # retry, it returns to the regular check interval.
        try:
            self.fail_min_interval = int(config.get('retry_min_interval',
                                                    '10'))
        except ValueError:
            self.log.critical("'retry_min_interval' config option must be an "
                              "integer")
            raise ConfigError(f"'retry_min_interval' option for {self.name} "
                              "notifier must be an integer") from None
        try:
            self.fail_max_interval = int(config.get('retry_max_interval',
                                                    '600'))
        except ValueError:
            self.log.critical("'retry_max_interval' config option must be an "
                              "integer")
            raise ConfigError(f"'retry_max_interval' option for {self.name} "
                              "notifier must be an integer") from None
        if (self.fail_min_interval > self.fail_max_interval or
                self.fail_min_interval <= 0 or
                self.fail_max_interval <= 0):
            self.log.critical("'retry_min_interval' option must be less than "
                              "'retry_max_interval' option and both must be "
                              "greater than 0")
            raise ConfigError("'retry_min_interval' option must be less than "
                              f"'retry_max_interval' option for {self.name} "
                              "notifier and both must be greater than 0")

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
