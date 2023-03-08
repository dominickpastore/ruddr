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

import ipaddress

import pytest

import doubles
import ruddr
from ruddr import PublishError, FatalPublishError


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
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
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

    def test_multiple_records_to_single(self, empty_addrfile, data_dir):
        """Test when multiple records are set for a host, they are replaced
        with a single record, but multiple records on irrelevant hosts are left
        alone."""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    # Different TTL within an RR set is not valid, but some
                    # providers may support it anyway. We take the minimum.
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('', ipaddress.IPv4Address('2.3.4.5'), 11),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                    ('foo', ipaddress.IPv4Address('2.3.4.5'), 22),
                    ('bar', ipaddress.IPv4Address('1.2.3.4'), 4),
                    ('bar', ipaddress.IPv4Address('2.3.4.5'), 44),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                    ('foo.bar', ipaddress.IPv4Address('2.3.4.5'), 33),
                    ('baz', ipaddress.IPv4Address('3.4.5.6'), 5),
                    ('baz', ipaddress.IPv4Address('4.5.6.7'), 55),
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
                'bar': ([ipaddress.IPv4Address('1.2.3.4'),
                         ipaddress.IPv4Address('2.3.4.5')], 4),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
                'baz': ([ipaddress.IPv4Address('3.4.5.6'),
                         ipaddress.IPv4Address('4.5.6.7')], 5),
            }),
        ]
        assert updater.put_subdomain_ipv4_calls == []

    @pytest.mark.parametrize(('zone', 'error'), [
        ('example.com', PublishError),
        ('example.com', FatalPublishError),
        ('example.net', PublishError),
        ('example.net', FatalPublishError),
    ])
    def test_put_zone_publish_error(self, empty_addrfile, data_dir,
                                    zone, error):
        """Test other zones are still published after PublishError for one
        zone's put_zone_ipv4s"""
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
                                   'example.net': None,
                                   zone: error},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
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

    @pytest.mark.parametrize(('zone', 'error'), [
        ('example.com', PublishError),
        ('example.com', FatalPublishError),
        ('example.net', PublishError),
        ('example.net', FatalPublishError),
    ])
    def test_fetch_zone_publish_error(self, empty_addrfile, data_dir,
                                      zone, error):
        """Test other zones still updated when fetch_zone_ipv4s raises
        PublishError for one zone"""
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
                zone: error,
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == []
        calls = [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]
        assert updater.put_zone_ipv4s_calls == [
            c for c in calls if c[0] != zone
        ]
        assert updater.put_subdomain_ipv4_calls == []

    def test_put_zone_not_implemented(self, empty_addrfile, data_dir):
        """Test that put_subdomain_ipv4 is used when fetch_zone_ipv4s is
        implemented but put_zone_ipv4 is not"""
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
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
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
        assert updater.put_subdomain_ipv4_calls == [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]

    def test_put_zone_not_implemented_extra_records(self, empty_addrfile,
                                                    data_dir):
        """Test that put_subdomain_ipv4 is not called for extra records
        returned by fetch_zone_ipv4s"""
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
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
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
        assert updater.put_subdomain_ipv4_calls == [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]

    def test_put_zone_not_implemented_missing_record(self, empty_addrfile,
                                                     data_dir):
        """Test missing record from fetch_zone_ipv4s is PublishError but other
        records still updated with put_subdomain_ipv4 when put_zone_ipv4s not
        implemented"""
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
            put_subdomain_ipv4_result={('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
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
        assert updater.put_subdomain_ipv4_calls == [
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]

    def test_put_zone_not_implemented_multiple_records_to_single(
        self, empty_addrfile, data_dir
    ):
        """Test when multiple records are set for a host and put_zone_ipv4s is
        not implemented, put_subdomain_ipv4 is called exactly once for each
        relevant host and not at all for irrelevant hosts"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv4s_result={
                'example.com': [
                    # Different TTL within an RR set is not valid, but some
                    # providers may support it anyway. We take the minimum.
                    ('', ipaddress.IPv4Address('1.2.3.4'), 1),
                    ('', ipaddress.IPv4Address('2.3.4.5'), 11),
                    ('foo', ipaddress.IPv4Address('1.2.3.4'), 2),
                    ('foo', ipaddress.IPv4Address('2.3.4.5'), 22),
                    ('bar', ipaddress.IPv4Address('1.2.3.4'), 4),
                    ('bar', ipaddress.IPv4Address('2.3.4.5'), 44),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv4Address('1.2.3.4'), 3),
                    ('foo.bar', ipaddress.IPv4Address('2.3.4.5'), 33),
                    ('baz', ipaddress.IPv4Address('3.4.5.6'), 5),
                    ('baz', ipaddress.IPv4Address('4.5.6.7'), 55),
                ],
            },
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
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
                'bar': ([ipaddress.IPv4Address('1.2.3.4'),
                         ipaddress.IPv4Address('2.3.4.5')], 4),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
                'baz': ([ipaddress.IPv4Address('3.4.5.6'),
                         ipaddress.IPv4Address('4.5.6.7')], 5),
            }),
        ]
        assert updater.put_subdomain_ipv4_calls == [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]

    @pytest.mark.parametrize(('subdomain', 'zone', 'error'), [
        ('', 'example.com', PublishError),
        ('', 'example.com', FatalPublishError),
        ('foo', 'example.com', PublishError),
        ('foo', 'example.com', FatalPublishError),
        ('foo.bar', 'example.net', PublishError),
        ('foo.bar', 'example.net', FatalPublishError),
    ])
    def test_put_zone_not_implemented_put_subdomain_publish_error(
        self, empty_addrfile, data_dir, subdomain, zone, error
    ):
        """Test that remaining subdomains and zones are still published when
        put_subdomain_ipv4 has a PublishError"""
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
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None,
                                       (subdomain, zone): error},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
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
        assert updater.put_subdomain_ipv4_calls == [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]

    @pytest.mark.parametrize(('zone', 'error'), [
        ('example.com', PublishError),
        ('example.com', FatalPublishError),
        ('example.net', PublishError),
        ('example.net', FatalPublishError),
    ])
    def test_put_zone_not_implemented_fetch_zone_publish_error(
        self, empty_addrfile, data_dir, zone, error
    ):
        """Test other zones still updated when fetch_zone_ipv4s raises
        PublishError for one zone and put_zone_ipv4s not implemented"""
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
                zone: error,
            },
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == []
        calls = [
            ('example.com', {
                '': ([ipaddress.IPv4Address('5.6.7.8')], 1),
                'foo': ([ipaddress.IPv4Address('5.6.7.8')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv4Address('5.6.7.8')], 3),
            }),
        ]
        assert updater.put_zone_ipv4s_calls == [
            c for c in calls if c[0] != zone
        ]
        calls = [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]
        assert updater.put_subdomain_ipv4_calls == [
            c for c in calls if c[1] != zone
        ]

    def test_put_zone_and_subdomain_not_implemented(self, empty_addrfile,
                                                    data_dir):
        """Test that FatalPublishError is raised when neither put_zone_ipv4s
        nor put_subdomain_ipv4 are implemented"""
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
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(FatalPublishError):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))


class TestFetchZoneIPv4sNotImplemented:
    def test_put_subdomain_preferred(self, empty_addrfile, data_dir):
        """Test that put_subdomain_ipv4 is used when fetch_zone_ipv4s is not
        implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv4s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv4s_calls == []
        assert updater.put_subdomain_ipv4_calls == [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]

    def test_put_subdomain_not_implemented(self, empty_addrfile, data_dir):
        """Test that when fetch_zone_ipv4s is not implemented,
        put_subdomain_ipv4 not implemented is a FatalPublishError even if
        put_zone_ipv4s is implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv4s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_zone_ipv4s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(FatalPublishError):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

    def test_multiple_records(self, empty_addrfile, data_dir):
        """Test that multiple records for a host from fetch_subdomain_ipv4s
        still lead to a single call to put_subdomain_ipv4"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv4s_result={
                # Different TTL within an RR set is not valid, but some
                # providers may support it anyway. We take the minimum.
                ('', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 1),
                    (ipaddress.IPv4Address('3.4.5.6'), 11),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 2),
                    (ipaddress.IPv4Address('3.4.5.6'), 22),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 3),
                    (ipaddress.IPv4Address('3.4.5.6'), 33),
                ],
            },
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv4s_calls == []
        assert updater.put_subdomain_ipv4_calls == [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]

    @pytest.mark.parametrize(('subdomain', 'zone', 'error'), [
        ('', 'example.com', PublishError),
        ('', 'example.com', FatalPublishError),
        ('foo', 'example.com', PublishError),
        ('foo', 'example.com', FatalPublishError),
        ('foo.bar', 'example.net', PublishError),
        ('foo.bar', 'example.net', FatalPublishError),
    ])
    def test_fetch_subdomain_publish_error(self, empty_addrfile, data_dir,
                                           subdomain, zone, error):
        """Test that remaining hosts are still updated when
        fetch_subdomain_ipv4s raises a PublishError for one of them"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv4s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
                (subdomain, zone): error,
            },
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv4s_calls == []
        calls = [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]
        assert updater.put_subdomain_ipv4_calls == [
            c for c in calls if c[0:2] != (subdomain, zone)
        ]

    @pytest.mark.parametrize(('subdomain', 'zone', 'error'), [
        ('', 'example.com', PublishError),
        ('', 'example.com', FatalPublishError),
        ('foo', 'example.com', PublishError),
        ('foo', 'example.com', FatalPublishError),
        ('foo.bar', 'example.net', PublishError),
        ('foo.bar', 'example.net', FatalPublishError),
    ])
    def test_put_subdomain_publish_error(self, empty_addrfile, data_dir,
                                         subdomain, zone, error):
        """Test that remaining hosts are still updated when put_subdomain_ipv4
        raises a PublishError for one of them"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv4s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv4Address('1.2.3.4'), 3),
                ],
            },
            put_subdomain_ipv4_result={('', 'example.com'): None,
                                       ('foo', 'example.com'): None,
                                       ('foo.bar', 'example.net'): None,
                                       (subdomain, zone): error},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))

        assert updater.fetch_zone_ipv4s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv4s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv4s_calls == []
        assert updater.put_subdomain_ipv4_calls == [
            ('', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
            ('foo', 'example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
            ('foo.bar', 'example.net', ipaddress.IPv4Address('5.6.7.8'), 3),
        ]


def test_fetch_zone_and_subdomain_ipv4_not_implemented(empty_addrfile,
                                                       data_dir):
    """Test that it's a FatalPublishError when neither fetch_zone_ipv4s nor
    fetch_subdomain_ipv4s are implemented"""
    updater = doubles.MockTwoWayZoneUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_zone_ipv4s_result={'example.com': None,
                               'example.net': None},
        put_subdomain_ipv4_result={('', 'example.com'): None,
                                   ('foo', 'example.com'): None,
                                   ('foo.bar', 'example.net'): None},
    )
    updater.init_hosts_and_zones(
        "example.com foo.bar.example.net foo.example.com"
    )
    with pytest.raises(FatalPublishError):
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))


class TestFetchZoneIPv6sImplemented:
    def test_fetch_and_put_zone_preferred(self, empty_addrfile, data_dir):
        """Test that fetch_zone_ipv6s and put_zone_ipv6s are preferred over
        fetch_subdomain_ipv6s and put_subdomain_ipv6 when all are
        implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            fetch_subdomain_ipv6s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv6Address('1234::1'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv6Address('1234::2'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None},
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == []

    def test_extra_records_untouched(self, empty_addrfile, data_dir):
        """Test extra records from fetch_zone_ipv6s are passed to
        put_zone_ipv6s untouched"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                    ('bar', ipaddress.IPv6Address('1234::4'), 4),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                    ('baz', ipaddress.IPv6Address('3456::5'), 5),
                ],
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
                'bar': ([ipaddress.IPv6Address('1234::4')], 4),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
                'baz': ([ipaddress.IPv6Address('3456::5')], 5),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == []

    def test_missing_record(self, empty_addrfile, data_dir):
        """Test missing record from fetch_zone_ipv6s is PublishError but other
        records still updated"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(PublishError):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == []

    def test_multiple_records(self, empty_addrfile, data_dir):
        """Test when multiple records are set for a host, they are all
        replaced, but multiple records on irrelevant hosts are left alone."""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    # Different TTL within an RR set is not valid, but some
                    # providers may support it anyway. We take the minimum.
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('', ipaddress.IPv6Address('2345::1'), 11),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                    ('foo', ipaddress.IPv6Address('1234::22'), 22),
                    ('bar', ipaddress.IPv6Address('1234::4'), 4),
                    ('bar', ipaddress.IPv6Address('2345::4'), 44),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                    ('foo.bar', ipaddress.IPv6Address('2345::33'), 33),
                    ('baz', ipaddress.IPv6Address('3456::5'), 5),
                    ('baz', ipaddress.IPv6Address('3456::55'), 55),
                ],
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/63'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2'),
                         ipaddress.IPv6Address('5678::22')], 2),
                'bar': ([ipaddress.IPv6Address('1234::4'),
                         ipaddress.IPv6Address('2345::4')], 4),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3'),
                             ipaddress.IPv6Address('5678::33')], 3),
                'baz': ([ipaddress.IPv6Address('3456::5'),
                         ipaddress.IPv6Address('3456::55')], 5),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == []

    @pytest.mark.parametrize(('zone', 'error'), [
        ('example.com', PublishError),
        ('example.com', FatalPublishError),
        ('example.net', PublishError),
        ('example.net', FatalPublishError),
    ])
    def test_put_zone_publish_error(self, empty_addrfile, data_dir,
                                    zone, error):
        """Test other zones are still published after PublishError for one
        zone's put_zone_ipv6s"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None,
                                   zone: error},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == []

    @pytest.mark.parametrize(('zone', 'error'), [
        ('example.com', PublishError),
        ('example.com', FatalPublishError),
        ('example.net', PublishError),
        ('example.net', FatalPublishError),
    ])
    def test_fetch_zone_publish_error(self, empty_addrfile, data_dir,
                                      zone, error):
        """Test other zones still updated when fetch_zone_ipv6s raises
        PublishError for one zone"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
                zone: error,
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        calls = [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_zone_ipv6s_calls == [
            c for c in calls if c[0] != zone
        ]
        assert updater.put_subdomain_ipv6s_calls == []

    def test_put_zone_not_implemented(self, empty_addrfile, data_dir):
        """Test that put_subdomain_ipv6s is used when fetch_zone_ipv6s is
        implemented but put_zone_ipv6 is not"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]

    def test_put_zone_not_implemented_extra_records(self, empty_addrfile,
                                                    data_dir):
        """Test that put_subdomain_ipv6s is not called for extra records
        returned by fetch_zone_ipv6s"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                    ('bar', ipaddress.IPv6Address('1234::4'), 4),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                    ('baz', ipaddress.IPv6Address('3456::5'), 5),
                ],
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
                'bar': ([ipaddress.IPv6Address('1234::4')], 4),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
                'baz': ([ipaddress.IPv6Address('3456::5')], 5),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]

    def test_put_zone_not_implemented_missing_record(self, empty_addrfile,
                                                     data_dir):
        """Test missing record from fetch_zone_ipv6s is PublishError but other
        records still updated with put_subdomain_ipv6s when put_zone_ipv6s not
        implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_subdomain_ipv6s_result={('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(PublishError):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == [
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]

    def test_put_zone_not_implemented_multiple_records(
        self, empty_addrfile, data_dir
    ):
        """Test when multiple records are set for a host and put_zone_ipv6s is
        not implemented, put_subdomain_ipv6s is called exactly once for each
        relevant host and not at all for irrelevant hosts"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    # Different TTL within an RR set is not valid, but some
                    # providers may support it anyway. We take the minimum.
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('', ipaddress.IPv6Address('2345::1'), 11),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                    ('foo', ipaddress.IPv6Address('1234::22'), 22),
                    ('bar', ipaddress.IPv6Address('1234::4'), 4),
                    ('bar', ipaddress.IPv6Address('2345::4'), 44),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                    ('foo.bar', ipaddress.IPv6Address('2345::33'), 33),
                    ('baz', ipaddress.IPv6Address('3456::5'), 5),
                    ('baz', ipaddress.IPv6Address('3456::55'), 55),
                ],
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2'),
                         ipaddress.IPv6Address('5678::22')], 2),
                'bar': ([ipaddress.IPv6Address('1234::4'),
                         ipaddress.IPv6Address('2345::4')], 4),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3'),
                             ipaddress.IPv6Address('5678::33')], 3),
                'baz': ([ipaddress.IPv6Address('3456::5'),
                         ipaddress.IPv6Address('3456::55')], 5),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2'),
                                    ipaddress.IPv6Address('5678::22')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3'),
                                        ipaddress.IPv6Address('5678::33')], 3),
        ]

    @pytest.mark.parametrize(('subdomain', 'zone', 'error'), [
        ('', 'example.com', PublishError),
        ('', 'example.com', FatalPublishError),
        ('foo', 'example.com', PublishError),
        ('foo', 'example.com', FatalPublishError),
        ('foo.bar', 'example.net', PublishError),
        ('foo.bar', 'example.net', FatalPublishError),
    ])
    def test_put_zone_not_implemented_put_subdomain_publish_error(
        self, empty_addrfile, data_dir, subdomain, zone, error
    ):
        """Test that remaining subdomains and zones are still published when
        put_subdomain_ipv6s has a PublishError"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None,
                                        (subdomain, zone): error},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        assert updater.put_zone_ipv6s_calls == [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_subdomain_ipv6s_calls == [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]

    @pytest.mark.parametrize(('zone', 'error'), [
        ('example.com', PublishError),
        ('example.com', FatalPublishError),
        ('example.net', PublishError),
        ('example.net', FatalPublishError),
    ])
    def test_put_zone_not_implemented_fetch_zone_publish_error(
        self, empty_addrfile, data_dir, zone, error
    ):
        """Test other zones still updated when fetch_zone_ipv4s raises
        PublishError for one zone and put_zone_ipv4s not implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
                zone: error,
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == []
        calls = [
            ('example.com', {
                '': ([ipaddress.IPv6Address('5678::1')], 1),
                'foo': ([ipaddress.IPv6Address('5678::2')], 2),
            }),
            ('example.net', {
                'foo.bar': ([ipaddress.IPv6Address('5678::3')], 3),
            }),
        ]
        assert updater.put_zone_ipv6s_calls == [
            c for c in calls if c[0] != zone
        ]
        calls = [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]
        assert updater.put_subdomain_ipv6s_calls == [
            c for c in calls if c[1] != zone
        ]

    def test_put_zone_and_subdomain_not_implemented(self, empty_addrfile,
                                                    data_dir):
        """Test that FatalPublishError is raised when neither put_zone_ipv6s
        nor put_subdomain_ipv6s are implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_zone_ipv6s_result={
                'example.com': [
                    ('', ipaddress.IPv6Address('1234::1'), 1),
                    ('foo', ipaddress.IPv6Address('1234::2'), 2),
                ],
                'example.net': [
                    ('foo.bar', ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(FatalPublishError):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))


class TestFetchZoneIPv6sNotImplemented:
    def test_put_subdomain_preferred(self, empty_addrfile, data_dir):
        """Test that put_subdomain_ipv6s is used when fetch_zone_ipv6s is not
        implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv6s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv6Address('1234::1'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv6Address('1234::2'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None},
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv6s_calls == []
        assert updater.put_subdomain_ipv6s_calls == [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]

    def test_put_subdomain_not_implemented(self, empty_addrfile, data_dir):
        """Test that when fetch_zone_ipv6s is not implemented,
        put_subdomain_ipv6s not implemented is a FatalPublishError even if
        put_zone_ipv6s is implemented"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv6s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv6Address('1234::1'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv6Address('1234::2'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_zone_ipv6s_result={'example.com': None,
                                   'example.net': None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(FatalPublishError):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

    def test_multiple_records(self, empty_addrfile, data_dir):
        """Test that multiple records for a host from fetch_subdomain_ipv6s
        still lead to a single call to put_subdomain_ipv6s"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv6s_result={
                # Different TTL within an RR set is not valid, but some
                # providers may support it anyway. We take the minimum.
                ('', 'example.com'): [
                    (ipaddress.IPv6Address('1234::1'), 1),
                    (ipaddress.IPv6Address('3456::1'), 11),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv6Address('1234::2'), 2),
                    (ipaddress.IPv6Address('1234::22'), 22),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv6Address('1234::3'), 3),
                    (ipaddress.IPv6Address('3456::33'), 33),
                ],
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv6s_calls == []
        assert updater.put_subdomain_ipv6s_calls == [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2'),
                                    ipaddress.IPv6Address('5678::22')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3'),
                                        ipaddress.IPv6Address('5678::33')], 3),
        ]

    @pytest.mark.parametrize(('subdomain', 'zone', 'error'), [
        ('', 'example.com', PublishError),
        ('', 'example.com', FatalPublishError),
        ('foo', 'example.com', PublishError),
        ('foo', 'example.com', FatalPublishError),
        ('foo.bar', 'example.net', PublishError),
        ('foo.bar', 'example.net', FatalPublishError),
    ])
    def test_fetch_subdomain_publish_error(self, empty_addrfile, data_dir,
                                           subdomain, zone, error):
        """Test that remaining hosts are still updated when
        fetch_subdomain_ipv6s raises a PublishError for one of them"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv6s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv6Address('1234::1'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv6Address('1234::2'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv6Address('1234::3'), 3),
                ],
                (subdomain, zone): error,
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv6s_calls == []
        calls = [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]
        assert updater.put_subdomain_ipv6s_calls == [
            c for c in calls if c[0:2] != (subdomain, zone)
        ]

    @pytest.mark.parametrize(('subdomain', 'zone', 'error'), [
        ('', 'example.com', PublishError),
        ('', 'example.com', FatalPublishError),
        ('foo', 'example.com', PublishError),
        ('foo', 'example.com', FatalPublishError),
        ('foo.bar', 'example.net', PublishError),
        ('foo.bar', 'example.net', FatalPublishError),
    ])
    def test_put_subdomain_publish_error(self, empty_addrfile, data_dir,
                                         subdomain, zone, error):
        """Test that remaining hosts are still updated when put_subdomain_ipv6s
        raises a PublishError for one of them"""
        updater = doubles.MockTwoWayZoneUpdater(
            'test_updater', empty_addrfile, data_dir,
            fetch_subdomain_ipv6s_result={
                ('', 'example.com'): [
                    (ipaddress.IPv6Address('1234::1'), 1),
                ],
                ('foo', 'example.com'): [
                    (ipaddress.IPv6Address('1234::2'), 2),
                ],
                ('foo.bar', 'example.net'): [
                    (ipaddress.IPv6Address('1234::3'), 3),
                ],
            },
            put_subdomain_ipv6s_result={('', 'example.com'): None,
                                        ('foo', 'example.com'): None,
                                        ('foo.bar', 'example.net'): None,
                                        (subdomain, zone): error},
        )
        updater.init_hosts_and_zones(
            "example.com foo.bar.example.net foo.example.com"
        )
        with pytest.raises(error):
            updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

        assert updater.fetch_zone_ipv6s_calls == [
            'example.com',
            'example.net',
        ]
        assert updater.fetch_subdomain_ipv6s_calls == [
            ('', 'example.com'),
            ('foo', 'example.com'),
            ('foo.bar', 'example.net'),
        ]
        assert updater.put_zone_ipv6s_calls == []
        assert updater.put_subdomain_ipv6s_calls == [
            ('', 'example.com', [ipaddress.IPv6Address('5678::1')], 1),
            ('foo', 'example.com', [ipaddress.IPv6Address('5678::2')], 2),
            ('foo.bar', 'example.net', [ipaddress.IPv6Address('5678::3')], 3),
        ]


def test_fetch_zone_and_subdomain_ipv6_not_implemented(empty_addrfile,
                                                       data_dir):
    """Test that it's a FatalPublishError when neither fetch_zone_ipv6s nor
    fetch_subdomain_ipv6s are implemented"""
    updater = doubles.MockTwoWayZoneUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_zone_ipv6s_result={'example.com': None,
                               'example.net': None},
        put_subdomain_ipv6s_result={('', 'example.com'): None,
                                    ('foo', 'example.com'): None,
                                    ('foo.bar', 'example.net'): None},
    )
    updater.init_hosts_and_zones(
        "example.com foo.bar.example.net foo.example.com"
    )
    with pytest.raises(FatalPublishError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))


def test_init_hosts_and_zones_structured(empty_addrfile, data_dir):
    """Test init_hosts_and_zones with structured input instead of raw string"""
    updater = doubles.MockTwoWayZoneUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_zone_ipv6s_result={
            'example.com': [
                ('', ipaddress.IPv6Address('1234::1'), 1),
                ('bar', ipaddress.IPv6Address('1234::4'), 4),
                ('foo', ipaddress.IPv6Address('1234::2'), 2),
            ],
            'bar.example.net': [
                ('foo', ipaddress.IPv6Address('1234::3'), 3),
            ],
        },
        put_zone_ipv6s_result={'example.com': None,
                               'bar.example.net': None},
    )
    updater.init_hosts_and_zones([
        ('example.com', None),
        ('foo.bar.example.net', 'bar.example.net'),
        ('bar.example.com', 'example.com'),
        ('foo.example.com', None),
    ])
    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))

    assert updater.fetch_zone_ipv6s_calls == [
        'example.com',
        'bar.example.net',
    ]
    assert updater.fetch_subdomain_ipv6s_calls == []
    assert updater.put_zone_ipv6s_calls == [
        ('example.com', {
            '': ([ipaddress.IPv6Address('5678::1')], 1),
            'bar': ([ipaddress.IPv6Address('5678::4')], 4),
            'foo': ([ipaddress.IPv6Address('5678::2')], 2),
        }),
        ('bar.example.net', {
            'foo': ([ipaddress.IPv6Address('5678::3')], 3),
        }),
    ]
    assert updater.put_subdomain_ipv6s_calls == []


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
