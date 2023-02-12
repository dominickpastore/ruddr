import ipaddress

import pytest

import doubles
import ruddr
from ruddr import PublishError


@pytest.fixture(scope='session')
def data_dir(tmp_path_factory):
    return str(tmp_path_factory.mktemp('data'))


@pytest.fixture
def mock_zone_splitter(mocker):
    doubles.MockZoneSplitter.clear_domains()
    mocker.patch("ruddr.util.ZoneSplitter", new=doubles.MockZoneSplitter)
    return doubles.MockZoneSplitter


class TestGetZones:
    def test_hardcoded_zones(
        self, empty_addrfile, data_dir, mock_zone_splitter
    ):
        """Test zones not fetched when all hosts have hardcoded zones"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
            },
            put_zone_ipv4s_result={'example.com': None},
        )
        updater.init_hosts_and_zones(
            "example.com/example.com foo.example.com/example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 0
        assert mock_zone_splitter.split_domains == []
        assert updater.fetch_zone_ipv4s_calls == ['example.com']
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
        ]

    def test_some_hardcoded(
        self, empty_addrfile, data_dir, mock_zone_splitter
    ):
        """Test hardcoded zones left untouched when others need to be
        fetched"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'bar.example.com': [
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'bar.example.com': None},
            get_zones_result=['example.com', 'bar.example.com'],
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.com/bar.example.com foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 1
        assert mock_zone_splitter.split_domains == []
        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'bar.example.com',
        ]
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('bar.example.com', {
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]

    def test_no_hardcoded(
        self, empty_addrfile, data_dir, mock_zone_splitter
    ):
        """Test zones are fetched when no zones are hardcoded"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
            get_zones_result=['example.com', 'example.net'],
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 1
        assert mock_zone_splitter.split_domains == []
        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]

    def test_get_zones_not_implemented(
        self, empty_addrfile, data_dir, mock_zone_splitter
    ):
        """Test zones are fetched from Public Suffix List when get_zones is not
        implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 1
        assert mock_zone_splitter.split_domains == [
            'example.com',
            'foo.bar.example.net',
            'foo.example.com',
        ]
        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]

    def test_publish_error(
        self, empty_addrfile, data_dir, mock_zone_splitter
    ):
        """Test publish_ipv4 stops and raises PublishError when get_zones
        raises PublishError"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
            get_zones_result=PublishError,
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(PublishError):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 1
        assert mock_zone_splitter.split_domains == []
        assert updater.fetch_zone_ipv4s_calls == []
        assert updater.put_zone_ipv4s_calls == []

    def test_no_matching_zone(
        self, empty_addrfile, data_dir, mock_zone_splitter
    ):
        """Test PublishError is raised when one of the configured hosts does
        not match any zone"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
            get_zones_result=['example.com', 'example.net'],
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com bar.example.org"
        )
        with pytest.raises(PublishError):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 1
        assert mock_zone_splitter.split_domains == []
        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]

    def test_extra_zone(
        self, empty_addrfile, data_dir, mock_zone_splitter
    ):
        """Test extra zones that don't match any host are present from
        get_zones and their records are not fetched"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
            get_zones_result=['example.com', 'example.net', 'example.org'],
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 1
        assert mock_zone_splitter.split_domains == []
        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]

    @pytest.mark.parametrize(('host', 'zones', 'subdomain', 'zone'), [
        ('bar.example.com',
         ['example.com', 'bar.example.com', 'example.net'],
         '',
         'bar.example.com'),
        ('bar.example.com',
         ['bar.example.com', 'example.com', 'example.net'],
         '',
         'bar.example.com'),
        ('foo.bar.example.com',
         ['example.com', 'bar.example.com', 'example.net'],
         'foo',
         'bar.example.com'),
        ('foo.bar.example.com',
         ['bar.example.com', 'example.com', 'example.net'],
         'foo',
         'bar.example.com'),
    ])
    def test_longest_zone_matched(
        self, host, zones, subdomain, zone,
        empty_addrfile, data_dir, mock_zone_splitter,
    ):
        """Test that a host is always matched with the longest zone possible"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
                zone: [
                    (subdomain, ipaddress.IPv4Address('1.2.3.4'), 4),
                ]
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None,
                                   zone: None},
            get_zones_result=zones,
        )
        updater.init_hosts_and_zones(
            f"example.com foo.bar.example.net foo.example.com {host}"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.get_zones_call_count == 1
        assert mock_zone_splitter.split_domains == []
        assert sorted(updater.fetch_zone_ipv4s_calls) == sorted(zones)
        assert sorted(updater.put_zone_ipv4s_calls) == sorted([
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
            (zone, {
                subdomain: ([ipaddress.IPv4Address('5.6.7.8')], 4),
            }),
        ])


class TestFetchZoneIPv4sImplemented:
    def test_fetch_and_put_zone_preferred(self, empty_addrfile, data_dir):
        """Test that fetch_zone_ipv4s and put_zone_ipv4s are preferred over
        fetch_subdomain_ipv4s and put_subdomain_ipv4 when all are
        implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            fetch_subdomain_ipv4s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                ('bar', 'example.net'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == []
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv4_calls == []

    def test_extra_records_untouched(self, empty_addrfile, data_dir):
        """Test extra records from fetch_zone_ipv4s are passed to
        put_zone_ipv4s untouched"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                    ('bar', ipaddress.IPv4Address('1.2.3.4'), 4),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                    ('baz', ipaddress.IPv4Address('3.4.5.6'), 5),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == []
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
                'bar': ([ipaddress.IPv4Address('1.2.3.4')], 4),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
                'baz': ([ipaddress.IPv4Address('3.4.5.6')], 5),
            }),
        ]
        assert updater.put_subdomain_ipv4_calls == []

    def test_missing_record(self, empty_addrfile, data_dir):
        """Test missing record from fetch_zone_ipv4s is PublishError but other
        records still updated"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(PublishError):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == []
        assert updater.put_zone_ipv4s_calls == [
            ('example.com', {
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv4_calls == []


# TODO fetch_zone_ipv4s implemented, multiple records on each host replaced
#  with single (extra records left alone)
# TODO fetch_zone_ipv4s implemented, put_zone_ipv4s raises PublishError, other
#  zones still updated
# TODO fetch_zone_ipv4s implemented, put_zone_ipv4s not implemented,
#  put_subdomain_ipv4 called instead (all single records)
# TODO fetch_zone_ipv4s implemented, put_zone_ipv4s not implemented,
#  put_subdomain_ipv4 called instead, but not for extra records
# TODO fetch_zone_ipv4s implemented, put_zone_ipv4s not implemented,
#  put_subdomain_ipv4 is implemented, missing record is PublishError, other
#  zones and other records still updated
# TODO fetch_zone_ipv4s implemented, put_zone_ipv4s not implemented,
#  put_subdomain_ipv4 called instead, only once when multiple records on hosts
# TODO fetch_zone_ipv4s implemented, put_zone_ipv4s not implemented,
#  put_subdomain_ipv4 raises PublishError, other domains in zone still updated
#  and other zones still updated
# TODO fetch_zone_ipv4s raises PublishError, other zones still updated
# TODO fetch_zone_ipv4s implemented, neither put_zone_ipv4s nor
#  put_subdomain_ipv4 implemented, raise FatalPublishError

# TODO fetch_zone_ipv4s not implemented, fetch_subdomain_ipv4s used instead,
#  all single records updated, put_zone_ipv4s and put_subdomain_ipv4
#  implemented, put_subdomain_ipv4 called only
# TODO fetch_zone_ipv4s not implemented, fetch_subdomain_ipv4s used instead,
#  put_zone_ipv4s implemented but put_subdomain_ipv4 not, FatalPublishError
# TODO fetch_zone_ipv4s not implemented, fetch_subdomain_ipv4s used instead,
#  fetch_subdomain_ipv4s raises PublishError, other subdomains and zones still
#  fetched and updated
# TODO fetch_zone_ipv4s not implemented, fetch_subdomain_ipv4s used instead,
#  multiple records on each host replaced with single
# TODO fetch_zone_ipv4s not implemented, fetch_subdomain_ipv4s used instead,
#  put_subdomain_ipv4 raises PublishError, other hosts and zones still updated

# TODO neither fetch_zone_ipv4s nor fetch_subdomain_ipv4s implemented, raise
#  FatalPublishError

# TODO fetch_zone_ipv6s implemented, all single records updated, put_zone_ipv6s
#  and put_subdomain_ipv6s implemented, put_zone_ipv6s preferred (and
#  fetch_subdomain_ipv6s implemented too but not preferred)
# TODO fetch_zone_ipv6s implemented, extra records left alone
# TODO fetch_zone_ipv6s implemented, missing record is PublishError, other
#  zones and other records still updated
# TODO fetch_zone_ipv6s implemented, multiple records on each host replaced
#  (extra records left alone)
# TODO fetch_zone_ipv6s implemented, put_zone_ipv6s raises PublishError, other
#  zones still updated
# TODO fetch_zone_ipv6s implemented, put_zone_ipv6s not implemented,
#  put_subdomain_ipv6s called instead (all single records)
# TODO fetch_zone_ipv6s implemented, put_zone_ipv6s not implemented,
#  put_subdomain_ipv6s called instead, but not for extra records
# TODO fetch_zone_ipv6s implemented, put_zone_ipv6s not implemented,
#  put_subdomain_ipv6s is implemented, missing record is PublishError, other
#  zones and other records still updated
# TODO fetch_zone_ipv6s implemented, put_zone_ipv6s not implemented,
#  put_subdomain_ipv6s called instead, only once when multiple records on hosts
# TODO fetch_zone_ipv6s implemented, put_zone_ipv6s not implemented,
#  put_subdomain_ipv6s raises PublishError, other domains in zone still updated
#  and other zones still updated
# TODO fetch_zone_ipv6s raises PublishError, other zones still updated
# TODO fetch_zone_ipv6s implemented, neither put_zone_ipv6s nor
#  put_subdomain_ipv6s implemented, raise FatalPublishError

# TODO fetch_zone_ipv6s not implemented, fetch_subdomain_ipv6s used instead,
#  all single records updated, put_zone_ipv6s and put_subdomain_ipv6s
#  implemented, put_subdomain_ipv6s called only
# TODO fetch_zone_ipv6s not implemented, fetch_subdomain_ipv6s used instead,
#  put_zone_ipv6s implemented but put_subdomain_ipv6s not, FatalPublishError
# TODO fetch_zone_ipv6s not implemented, fetch_subdomain_ipv6s used instead,
#  fetch_subdomain_ipv6s raises PublishError, other subdomains and zones still
#  fetched and updated
# TODO fetch_zone_ipv6s not implemented, fetch_subdomain_ipv6s used instead,
#  multiple records on each host replaced with single
# TODO fetch_zone_ipv6s not implemented, fetch_subdomain_ipv6s used instead,
#  put_subdomain_ipv6s raises PublishError, other hosts and zones still updated

# TODO neither fetch_zone_ipv6s nor fetch_subdomain_ipv6s implemented, raise
#  FatalPublishError

# TODO Test init_hosts_and_zones with structured hosts, and do an IPv6 update
#  to confirm it works (all others tests will use string hosts)


# fqdn, zone, subdomain
subdomain_cases = [
    ('', '', ''),
    ('com', 'com', ''),
    ('com', '', 'com'),
    ('example.com', 'example.com', ''),
    ('example.com', 'com', 'example'),
    ('example.com', '', 'example.com'),
    ('www.example.com', 'www.example.com', ''),
    ('www.example.com', 'example.com', 'www'),
    ('www.example.com', 'com', 'www.example'),
    ('www.example.com', '', 'www.example.com'),
]


@pytest.mark.parametrize(('fqdn', 'zone', 'subdomain'), subdomain_cases)
def test_subdomain_of(fqdn, zone, subdomain):
    assert ruddr.TwoWayZoneUpdater.subdomain_of(fqdn, zone) == subdomain


@pytest.mark.parametrize(('fqdn', 'zone', 'subdomain'), subdomain_cases)
def test_fqdn_of(fqdn, zone, subdomain):
    assert ruddr.TwoWayZoneUpdater.fqdn_of(subdomain, zone) == fqdn
