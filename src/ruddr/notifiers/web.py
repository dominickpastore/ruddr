"""Ruddr notifier that checks the IP address using a what-is-my-ip-style
website"""

import ipaddress
import socket
import requests

from ruddr.configuration import USER_AGENT
from ruddr.exceptions import NotifyError, ConfigError
from ruddr.util import RequestsFamilyRestriction
from .notifier import Notifier


class WebNotifier(Notifier):
    """Ruddr notifier that checks the IP address using a what-is-my-ip-style
    website"""

    def __init__(self, name, config):
        super().__init__(name, config)

        # URL to request IP addresses from. Normally, both IPv4 and IPv6
        # addresses will be requested from the same URL (by issuing separate
        # requests over IPv4 and IPv6). If a different URL should be used for
        # IPv4 and IPv6, specify the IPv6 URL with "url6=".
        #
        # If only IPv4 is needed, use "notifier4=" to attach this notifier to
        # updaters in the config instead of plain "notifier=". When there are
        # no updaters requesting IPv6 addresses from this notifier, it will
        # skip checking the IPv6 address. (Vice versa for skipping IPv4.)
        try:
            self.url4 = config['url']
        except KeyError:
            self.log.critical("'url' config option is required. Only need "
                              "IPv6? Use 'url=' and attach this notifier to "
                              "an updater with 'notifier6='.")
            raise ConfigError(f"{self.name} notifier requires 'url' config "
                              "option") from None

        # URL to request IPv6 addresses from, if different from the URL to
        # request IPv4 addresses. (If only IPv6 is needed, there is no need to
        # use this option. Instead, use the regular 'url=' option, and attach
        # this notifier to an updater with 'notifier6='. It will only request
        # IPv6 addresses.)
        try:
            self.url6 = config['url6']
        except KeyError:
            self.url6 = self.url4

        # Timeout to use waiting for a response from the HTTP server, in
        # seconds
        try:
            self.timeout4 = float(config.get('timeout', '10'))
        except ValueError:
            self.log.critical("'timeout' config option must be a number")
            raise ConfigError(f"'timeout' option for {self.name} notifier "
                              "must be a number") from None

        # Timeout to use waiting for a response from the HTTP server, in
        # seconds
        try:
            self.timeout6 = float(config['timeout6'])
        except KeyError:
            self.timeout6 = self.timeout4
        except ValueError:
            self.log.critical("'timeout6' config option must be a number")
            raise ConfigError(f"'timeout6' option for {self.name} notifier "
                              "must be a number") from None

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

        self.set_check_intervals(retry_min_interval=60,
                                 retry_max_interval=86400,
                                 success_interval=10800,
                                 config=config)

    def check_once(self):
        self.log.info("Checking IP addresses.")

        # None if not wanted, otherwise True if assigned, False if not assigned
        got_ipv4 = None
        got_ipv6 = None
        # True if there is an HTTP error, suggesting something went wrong
        # rather than this host simply not having connectivity on that address
        # family right now (the latter case not always being a problem--but
        # we'll check later)
        err_ipv4 = False
        err_ipv6 = False

        if self.want_ipv4():
            with RequestsFamilyRestriction(socket.AF_INET):
                try:
                    r = requests.get(self.url4, timeout=self.timeout4,
                                     headers={'User-Agent': USER_AGENT})
                except requests.exceptions.RequestException as e:
                    self.log.error("Could not get IPv4 from %s: %s",
                                   self.url4, e)
                    got_ipv4 = False
                else:
                    try:
                        r.raise_for_status()
                    except requests.exceptions.HTTPError:
                        self.log.error("Received HTTP %d from %s: %s",
                                       r.status_code, self.url4, r.text)
                        got_ipv4 = False
                        err_ipv4 = True
                    else:
                        got_ipv4 = True
                        ipv4_text = r.text
            if got_ipv4:
                try:
                    ipv4 = ipaddress.IPv4Address(ipv4_text.strip())
                except ValueError:
                    self.log.error('Response from %s did not contain valid '
                                   'IPv4 address: "%s"', self.url4, ipv4_text)
                    got_ipv4 = False
                else:
                    self.notify_ipv4(ipv4)

        if self.want_ipv6():
            with RequestsFamilyRestriction(socket.AF_INET6):
                try:
                    r = requests.get(self.url6, timeout=self.timeout6,
                                     headers={'User-Agent': USER_AGENT})
                except requests.exceptions.RequestException as e:
                    self.log.error("Could not get IPv6 from %s: %s",
                                   self.url6, e)
                    got_ipv6 = False
                else:
                    try:
                        r.raise_for_status()
                    except requests.exceptions.HTTPError:
                        self.log.error("Received HTTP %d from %s: %s",
                                       r.status_code, self.url6, r.text)
                        got_ipv6 = False
                        err_ipv6 = True
                    else:
                        got_ipv6 = True
                        ipv6_text = r.text
            if got_ipv6:
                try:
                    ipv6 = ipaddress.IPv6Interface(
                        (ipv6_text.strip(), self.ipv6_prefix)).network
                except ValueError:
                    self.log.error('Response from %s did not contain valid '
                                   'IPv6 address: "%s"', self.url6, ipv6_text)
                    got_ipv6 = False
                else:
                    self.notify_ipv6(ipv6)

        # Raise for HTTP errors
        if err_ipv4:
            raise NotifyError(f"HTTP error for IPv4 in {self.name} notifier")
        if err_ipv6:
            raise NotifyError(f"HTTP error for IPv6 in {self.name} notifier")

        # Error if no wanted address was found
        if not (got_ipv4 or got_ipv6):
            raise NotifyError(f"Could not get any IP address for {self.name} "
                              "notifier")

        # Error for any missing wanted and needed addresses
        if self.need_ipv4() and not got_ipv4:
            raise NotifyError(f"Could not get IPv4 address for {self.name} "
                              "notifier")
        if self.need_ipv6() and not got_ipv6:
            raise NotifyError(f"Could not get IPv6 address for {self.name} "
                              "notifier")
