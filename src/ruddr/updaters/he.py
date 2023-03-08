#  Ruddr - Robotic Updater for Dynamic DNS Records
#  Copyright (C) 2023 Dominick C. Pastore
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Ruddr updater for the IPv4 address at Hurricane Electric's tunnel broker"""

import requests

from ..configuration import USER_AGENT
from ..exceptions import ConfigError, PublishError
from .updater import Updater


class HEUpdater(Updater):
    """Ruddr updater for the IPv4 address at Hurricane Electric's tunnel broker

    :param name: Name of the updater (from config section heading)
    :param addrfile: The :class:`~ruddr.Addrfile` object
    :param config: Dict of config options for this updater
    """

    def __init__(self, name, addrfile, config):
        super().__init__(name, addrfile)

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
            raise ConfigError(f"{self.name} updater requires 'username' config"
                              " option") from None

        # HE password
        try:
            password = config['password']
        except KeyError:
            self.log.critical("'password' config option is required")
            raise ConfigError(f"{self.name} updater requires 'password' config"
                              " option") from None

        self.auth = (username, password)

        # HE update URL
        self.endpoint = config.get('url',
                                   'https://ipv4.tunnelbroker.net/nic/update')

    def publish_ipv4(self, address):
        params = {'hostname': self.tunnel,
                  'myip': address.exploded}
        headers = {'User-Agent': USER_AGENT}
        try:
            r = requests.get(self.endpoint, auth=self.auth,
                             params=params, headers=headers)
        except requests.exceptions.RequestException as e:
            self.log.error("Could not update tunnel %s client IPv4 to %s: %s",
                           self.tunnel, address.exploded, e)
            raise PublishError("Updater %s could not access %s: %s" % (
                self.name, self.endpoint, e)) from e

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log.error("Received HTTP %d when trying to update tunnel %s "
                           "client ipv4 to %s:\n%s", r.status_code,
                           self.tunnel, address.exploded, r.text)
            raise PublishError("Updater %s got HTTP %d for %s" % (
                self.name, r.status_code, self.endpoint)) from e

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
