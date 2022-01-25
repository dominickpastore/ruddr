from ruddr import Updater, Notifier


class MockUpdater(Updater):
    """Simple mock updater that keeps a list of IP updates it receives"""

    def __init__(self, name, config):
        super().__init__(name, config)
        self.published_addresses = []

    def publish_ipv4(self, address):
        self.published_addresses.append(address)

    def publish_ipv6(self, network):
        self.published_addresses.append(network)


class MockNotifier(Notifier):
    """A simple notifier that notifies on demand"""
    # Note: Tests can trigger notifying by calling .notify_ipv4() and
    # .notify_ipv6() directly

    def __init__(self, name, config):
        super().__init__(name, config)
        # Config vars to test .ipv4_ready() and .ipv6_ready()
        self._ipv4_ready = (config.get('ipv4_ready', 'true').lower() in
                            ('true', 'yes', 'on', '1'))
        self._ipv6_ready = (config.get('ipv4_ready', 'true').lower() in
                            ('true', 'yes', 'on', '1'))

    def ipv4_ready(self):
        return self._ipv4_ready

    def ipv6_ready(self):
        return self._ipv6_ready