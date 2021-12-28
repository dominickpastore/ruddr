"""Ruddr updater for the IPv4 address at Hurricane Electric's tunnel broker"""

import requests

from ..exceptions import ConfigError, PublishError
from .updater import Updater


class HEUpdater(Updater):
    """Ruddr updater for the IPv4 address at Hurricane Electric's tunnel broker

    :param name: Name of the updater (from config section heading)
    :param manager: The DDNSManager
    :param global_config: Dict of ``[ruddr]`` config options
    :param config: Dict of config options for this updater
    """

    def __init__(self, name, manager, global_config, config):
        super().__init__(name, manager, global_config, config)

        # HE tunnel ID
        try:
            self.tunnel = config['tunnel']
        except KeyError:
            self.log.critical("'tunnel' config option is required")
            raise ConfigError(f"{self.name} updater requires 'tunnel' config "
                              "option") from None

        # HE username
        try:
            username = config['username']
        except KeyError:
            self.log.critical("'username' config option is required")
            raise ConfigError(f"{self.name} updater requires 'username' config "
                              "option") from None

        # HE password
        try:
            password = config['password']
        except KeyError:
            self.log.critical("'password' config option is required")
            raise ConfigError(f"{self.name} updater requires 'password' config "
                              "option") from None

        self.auth = (username, password)

        # HE update URL
        self.endpoint = config.get('url',
                                   'https://ipv4.tunnelbroker.net/nic/update')

    def publish_ipv4(self, address):
        params = {'hostname': self.tunnel,
                  'myip': address.exploded}
        try:
            r = requests.get(self.endpoint, auth=self.auth, params=params)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log.error("Received HTTP %d when trying to update tunnel %s "
                           "client ipv4 to %s:\n%s", r.status_code,
                           self.tunnel, address.exploded, r.text)
            raise PublishError("Updater %s got HTTP %d for %s" % (
                self.name, r.status_code, self.endpoint)) from e
        except requests.exceptions.RequestException as e:
            self.log.error("Could not update tunnel %s client IPv4 to %s: %s",
                           self.tunnel, address.exploded, e)
            raise PublishError("Updater %s could not access %s: %s" % (
                self.name, self.endpoint, e)) from e

        response = r.text.strip().split()
        if response[0] == 'good':
            self.log.info("Tunnel %s client IPv4 updated to %s",
                          self.tunnel, address.exploded)
            return
        if response[0] == 'nochg':
            self.log.info("Tunnel %s client IPv4 already set to %s",
                          self.tunnel, address.exploded)
            return
        else:
            self.log.error('Server returned response "%s" when trying to '
                           'update tunnel %s client IPv4 to %s',
                           r.text, self.tunnel, address.exploded)
            raise PublishError("Updater %s got response from server: %s" %
                               (self.name, r.text))

    def publish_ipv6(self, network):
        self.log.debug("HE updater ignoring an IPv6 update")
