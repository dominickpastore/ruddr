from ruddr import Updater


class MockUpdater(Updater):
    """Simple mock updater that keeps a list of IP updates it receives"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.published_addresses = []

    def publish_ipv4(self, address):
        self.published_addresses.append(address)

    def publish_ipv6(self, network):
        self.published_addresses.append(network)
