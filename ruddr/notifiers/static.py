"""Ruddr notifier that returns a statically-configured IP address"""

import ipaddress

from ..exceptions import ConfigError
from .notifier import Notifier


class StaticNotifier(Notifier):
    """Ruddr notifier that returns a statically-configured IP address"""

    def __init__(self, name, config):
        super().__init__(name, config)

        # Static IPv4 address to use
        self.ipv4 = config.get('ipv4', None)
        if self.ipv4 is not None:
            try:
                self.ipv4 = ipaddress.IPv4Address(self.ipv4)
            except ValueError:
                self.log.critical("'ipv4' option contains an invalid IPv4 "
                                  "address")
                raise ConfigError(f"{self.name} notifier contains invalid "
                                  "address for 'ipv4' option") from None

        # Static IPv6 address with prefix to use. The prefix must be provided,
        # e.g. "1:2345::/64"
        self.ipv6 = config.get('ipv6', None)
        if self.ipv6 is not None:
            try:
                self.ipv6 = ipaddress.IPv6Network(self.ipv6)
            except ValueError:
                self.log.critical("'ipv6' option contains an invalid IPv6 "
                                  "address or no prefix")
                raise ConfigError(f"{self.name} notifier contains invalid "
                                  "address or no prefix for 'ipv6' option"
                                  ) from None

        if self.ipv4 is None and self.ipv6 is None:
            self.log.critical("No 'ipv4' or 'ipv6' option")
            raise ConfigError(f"{self.name} notifier requires either an IPv4 "
                              " or IPv6 address configured")

    def ipv4_ready(self):
        return self.ipv4 is not None

    def ipv6_ready(self):
        return self.ipv6 is not None

    def check_once(self):
        self.log.info("Checking IP addresses.")

        # No need to ensure the proper self.ipv4 or self.ipv6 variables are
        # set. The Notifier superclass already checked ipv4_ready() and
        # ipv6_ready().

        if self.want_ipv4():
            self.notify_ipv4(self.ipv4)
        if self.want_ipv6():
            self.notify_ipv6(self.ipv6)

    def start(self):
        self.log.debug("Nothing to start for StaticNotifier")

    def stop(self):
        self.log.debug("Nothing to stop for StaticNotifier")
