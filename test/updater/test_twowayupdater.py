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
from ruddr import PublishError


def test_init_hosts_str(empty_addrfile, data_dir):
    """Test init_hosts with raw string and the rest of the full flow"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_domain_ipv4s_result={
            'example.com': [(ipaddress.IPv4Address('1.2.3.4'), 1)],
            'foo.example.com': [(ipaddress.IPv4Address('1.2.3.4'), 2),
                                (ipaddress.IPv4Address('3.4.5.6'), 3)],
            'foo.bar.example.net': [(ipaddress.IPv4Address('3.4.5.6'), 4)],
        },
        fetch_all_ipv6s_result=[
            ('example.com', ipaddress.IPv6Address('1234::1'), 1),
            ('foo.example.com', ipaddress.IPv6Address('1234::2'), 2),
            ('foo.example.com', ipaddress.IPv6Address('3456::2'), 3),
            ('foo.bar.example.net', ipaddress.IPv6Address('3456::4'), 4),
            ('foo.bar.example.net', ipaddress.IPv6Address('3456::5'), 5),
            ('bar.example.org', ipaddress.IPv6Address('2345::6'), 6),
            ('bar.example.org', ipaddress.IPv6Address('4567::7'), 7),
        ],
        put_domain_ipv4_result={'example.com': None,
                                'foo.example.com': None,
                                'foo.bar.example.net': None},
        put_all_ipv6s_result=True,
    )
    updater.init_hosts('example.com foo.bar.example.net foo.example.com')

    updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    assert updater.fetch_all_ipv4s_count == 1
    assert updater.fetch_domain_ipv4s_calls == [
        'example.com',
        'foo.bar.example.net',
        'foo.example.com',
    ]
    assert updater.put_all_ipv4s_calls == []
    assert updater.put_domain_ipv4_calls == [
        ('example.com', ipaddress.IPv4Address('5.6.7.8'), 1),
        ('foo.bar.example.net', ipaddress.IPv4Address('5.6.7.8'), 4),
        ('foo.example.com', ipaddress.IPv4Address('5.6.7.8'), 2),
    ]

    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.fetch_all_ipv6s_count == 1
    assert updater.fetch_domain_ipv6s_calls == []
    assert updater.put_all_ipv6s_calls == [
        {'example.com': ([ipaddress.IPv6Address('5678::1')], 1),
         'foo.bar.example.net': ([ipaddress.IPv6Address('5678::4'),
                                  ipaddress.IPv6Address('5678::5')], 4),
         'foo.example.com': ([ipaddress.IPv6Address('5678::2')], 2),
         'bar.example.org': ([ipaddress.IPv6Address('2345::6'),
                              ipaddress.IPv6Address('4567::7')], 6)},
    ]
    assert updater.put_domain_ipv6s_calls == []


def test_init_hosts_list(empty_addrfile, data_dir):
    """Test init_hosts with list of domains and the rest of the full flow"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_all_ipv4s_result=[
            ('example.com', ipaddress.IPv4Address('1.2.3.4'), 1),
            ('foo.example.com', ipaddress.IPv4Address('1.2.3.4'), 2),
            ('foo.example.com', ipaddress.IPv4Address('3.4.5.6'), 3),
            ('foo.bar.example.net', ipaddress.IPv4Address('3.4.5.6'), 4),
            ('bar.example.org', ipaddress.IPv4Address('2.3.4.5'), 6),
            ('bar.example.org', ipaddress.IPv4Address('4.5.6.7'), 7),
        ],
        fetch_domain_ipv6s_result={
            'example.com': [(ipaddress.IPv6Address('1234::1'), 1)],
            'foo.example.com': [(ipaddress.IPv6Address('1234::2'), 2),
                                (ipaddress.IPv6Address('3456::2'), 3)],
            'foo.bar.example.net': [(ipaddress.IPv6Address('3456::4'), 4),
                                    (ipaddress.IPv6Address('3456::5'), 5)],
        },
        put_all_ipv4s_result=True,
        put_domain_ipv6s_result={'example.com': None,
                                 'foo.example.com': None,
                                 'foo.bar.example.net': None},
    )
    updater.init_hosts(
        ['example.com', 'foo.bar.example.net', 'foo.example.com']
    )

    updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    assert updater.fetch_all_ipv4s_count == 1
    assert updater.fetch_domain_ipv4s_calls == []
    assert updater.put_all_ipv4s_calls == [
        {'example.com': ([ipaddress.IPv4Address('5.6.7.8')], 1),
         'foo.bar.example.net': ([ipaddress.IPv4Address('5.6.7.8')], 4),
         'foo.example.com': ([ipaddress.IPv4Address('5.6.7.8')], 2),
         'bar.example.org': ([ipaddress.IPv4Address('2.3.4.5'),
                              ipaddress.IPv4Address('4.5.6.7')], 6)},
    ]
    assert updater.put_domain_ipv4_calls == []

    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.fetch_all_ipv6s_count == 1
    assert updater.fetch_domain_ipv6s_calls == [
        'example.com',
        'foo.bar.example.net',
        'foo.example.com',
    ]
    assert updater.put_all_ipv6s_calls == []
    assert updater.put_domain_ipv6s_calls == [
        ('example.com', [ipaddress.IPv6Address('5678::1')], 1),
        ('foo.bar.example.net', [ipaddress.IPv6Address('5678::4'),
                                 ipaddress.IPv6Address('5678::5')], 4),
        ('foo.example.com', [ipaddress.IPv6Address('5678::2')], 2),
    ]


def test_fetch_all_ipv4s(empty_addrfile, data_dir):
    """Test fetch_zone_ipv4s calls fetch_all_ipv4s"""
    result = [
        ('example.com', ipaddress.IPv4Address('1.2.3.4'), 1),
        ('foo.example.com', ipaddress.IPv4Address('1.2.3.4'), 2),
        ('foo.example.com', ipaddress.IPv4Address('3.4.5.6'), 3),
        ('foo.bar.example.net', ipaddress.IPv4Address('3.4.5.6'), 4),
        ('bar.example.org', ipaddress.IPv4Address('2.3.4.5'), 6),
        ('bar.example.org', ipaddress.IPv4Address('4.5.6.7'), 7),
    ]
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_all_ipv4s_result=result,
    )
    assert updater.fetch_zone_ipv4s('') == result
    assert updater.fetch_all_ipv4s_count == 1


def test_fetch_all_ipv4s_not_implemented(empty_addrfile, data_dir):
    """Test fetch_zone_ipv4s raises NotImplementedError when fetch_all_ipv4s
    is not implemented"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.fetch_zone_ipv4s('')
    assert updater.fetch_all_ipv4s_count == 1


def test_fetch_all_ipv4s_publish_error(empty_addrfile, data_dir):
    """Test fetch_zone_ipv4s raises PublishError when fetch_all_ipv4s does"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_all_ipv4s_result=PublishError,
    )
    with pytest.raises(PublishError):
        updater.fetch_zone_ipv4s('')
    assert updater.fetch_all_ipv4s_count == 1


def test_fetch_domain_ipv4s(empty_addrfile, data_dir):
    """Test fetch_subdomain_ipv4s calls fetch_domain_ipv4s"""
    result = {
        'example.com': [(ipaddress.IPv4Address('1.2.3.4'), 1)],
    }
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_domain_ipv4s_result=result,
    )
    assert updater.fetch_subdomain_ipv4s(
        'example.com', ''
    ) == result['example.com']
    assert updater.fetch_domain_ipv4s_calls == ['example.com']


def test_fetch_domain_ipv4s_not_implemented(empty_addrfile, data_dir):
    """Test fetch_subdomain_ipv4s raises NotImplementedError when
    fetch_domain_ipv4s is not implemented"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.fetch_subdomain_ipv4s('example.com', '')
    assert updater.fetch_domain_ipv4s_calls == ['example.com']


def test_fetch_domain_ipv4s_publish_error(empty_addrfile, data_dir):
    """Test fetch_subdomain_ipv4s raises PublishError when fetch_domain_ipv4s
    does"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_domain_ipv4s_result={'example.com': PublishError},
    )
    with pytest.raises(PublishError):
        updater.fetch_subdomain_ipv4s('example.com', '')
    assert updater.fetch_domain_ipv4s_calls == ['example.com']


def test_put_all_ipv4s(empty_addrfile, data_dir):
    """Test put_zone_ipv4s calls put_all_ipv4s"""
    arg = {'example.com': ([ipaddress.IPv4Address('5.6.7.8')], 1),
           'foo.bar.example.net': ([ipaddress.IPv4Address('5.6.7.8')], 4),
           'foo.example.com': ([ipaddress.IPv4Address('5.6.7.8')], 2),
           'bar.example.org': ([ipaddress.IPv4Address('2.3.4.5'),
                                ipaddress.IPv4Address('4.5.6.7')], 6)}
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_all_ipv4s_result=True,
    )
    updater.put_zone_ipv4s('', arg)
    assert updater.put_all_ipv4s_calls == [arg]


def test_put_all_ipv4s_not_implemented(empty_addrfile, data_dir):
    """Test put_zone_ipv4s raises NotImplementedError when put_all_ipv4s
    is not implemented"""
    arg = {'example.com': ([ipaddress.IPv4Address('5.6.7.8')], 1),
           'foo.bar.example.net': ([ipaddress.IPv4Address('5.6.7.8')], 4),
           'foo.example.com': ([ipaddress.IPv4Address('5.6.7.8')], 2),
           'bar.example.org': ([ipaddress.IPv4Address('2.3.4.5'),
                                ipaddress.IPv4Address('4.5.6.7')], 6)}
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.put_zone_ipv4s('', arg)
    assert updater.put_all_ipv4s_calls == [arg]


def test_put_all_ipv4s_publish_error(empty_addrfile, data_dir):
    """Test put_zone_ipv4s raises PublishError when put_all_ipv4s does"""
    arg = {'example.com': ([ipaddress.IPv4Address('5.6.7.8')], 1),
           'foo.bar.example.net': ([ipaddress.IPv4Address('5.6.7.8')], 4),
           'foo.example.com': ([ipaddress.IPv4Address('5.6.7.8')], 2),
           'bar.example.org': ([ipaddress.IPv4Address('2.3.4.5'),
                                ipaddress.IPv4Address('4.5.6.7')], 6)}
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_all_ipv4s_result=PublishError,
    )
    with pytest.raises(PublishError):
        updater.put_zone_ipv4s('', arg)
    assert updater.put_all_ipv4s_calls == [arg]


def test_put_domain_ipv4(empty_addrfile, data_dir):
    """Test put_subdomain_ipv4 calls put_domain_ipv4"""
    address = ipaddress.IPv4Address('5.6.7.8')
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_domain_ipv4_result={'example.com': None},
    )
    updater.put_subdomain_ipv4('example.com', '', address, 2)
    assert updater.put_domain_ipv4_calls == [('example.com', address, 2)]


def test_put_domain_ipv4_not_implemented(empty_addrfile, data_dir):
    """Test put_subdomain_ipv4 raises NotImplementedError when put_domain_ipv4
    is not implemented"""
    address = ipaddress.IPv4Address('5.6.7.8')
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.put_subdomain_ipv4('example.com', '', address, 2)
    assert updater.put_domain_ipv4_calls == [('example.com', address, 2)]


def test_put_domain_ipv4_publish_error(empty_addrfile, data_dir):
    """Test put_subdomain_ipv4 raises PublishError when put_domain_ipv4
    does"""
    address = ipaddress.IPv4Address('5.6.7.8')
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_domain_ipv4_result={'example.com': PublishError},
    )
    with pytest.raises(PublishError):
        updater.put_subdomain_ipv4('example.com', '', address, 2)
    assert updater.put_domain_ipv4_calls == [('example.com', address, 2)]


def test_fetch_all_ipv6s(empty_addrfile, data_dir):
    """Test fetch_zone_ipv6s calls fetch_all_ipv6s"""
    result = [
        ('example.com', ipaddress.IPv6Address('1234::1'), 1),
        ('foo.example.com', ipaddress.IPv6Address('1234::2'), 2),
        ('foo.example.com', ipaddress.IPv6Address('3456::2'), 3),
        ('foo.bar.example.net', ipaddress.IPv6Address('3456::4'), 4),
        ('foo.bar.example.net', ipaddress.IPv6Address('3456::5'), 5),
        ('bar.example.org', ipaddress.IPv6Address('2345::6'), 6),
        ('bar.example.org', ipaddress.IPv6Address('4567::7'), 7),
    ]
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_all_ipv6s_result=result,
    )
    assert updater.fetch_zone_ipv6s('') == result
    assert updater.fetch_all_ipv6s_count == 1


def test_fetch_all_ipv6s_not_implemented(empty_addrfile, data_dir):
    """Test fetch_zone_ipv6s raises NotImplementedError when fetch_all_ipv6s
    is not implemented"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.fetch_zone_ipv6s('')
    assert updater.fetch_all_ipv6s_count == 1


def test_fetch_all_ipv6s_publish_error(empty_addrfile, data_dir):
    """Test fetch_zone_ipv6s raises PublishError when fetch_all_ipv6s does"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_all_ipv6s_result=PublishError,
    )
    with pytest.raises(PublishError):
        updater.fetch_zone_ipv6s('')
    assert updater.fetch_all_ipv6s_count == 1


def test_fetch_domain_ipv6s(empty_addrfile, data_dir):
    """Test fetch_subdomain_ipv6s calls fetch_domain_ipv6s"""
    result = {
        'example.com': [(ipaddress.IPv6Address('1234::1'), 1)],
    }
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_domain_ipv6s_result=result,
    )
    assert updater.fetch_subdomain_ipv6s(
        'example.com', ''
    ) == result['example.com']
    assert updater.fetch_domain_ipv6s_calls == ['example.com']


def test_fetch_domain_ipv6s_not_implemented(empty_addrfile, data_dir):
    """Test fetch_subdomain_ipv6s raises NotImplementedError when
    fetch_domain_ipv6s is not implemented"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.fetch_subdomain_ipv6s('example.com', '')
    assert updater.fetch_domain_ipv6s_calls == ['example.com']


def test_fetch_domain_ipv6s_publish_error(empty_addrfile, data_dir):
    """Test fetch_subdomain_ipv6s raises PublishError when fetch_domain_ipv6s
    does"""
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        fetch_domain_ipv6s_result={'example.com': PublishError},
    )
    with pytest.raises(PublishError):
        updater.fetch_subdomain_ipv6s('example.com', '')
    assert updater.fetch_domain_ipv6s_calls == ['example.com']


def test_put_all_ipv6s(empty_addrfile, data_dir):
    """Test put_zone_ipv6s calls put_all_ipv6s"""
    arg = {'example.com': ([ipaddress.IPv6Address('5678::1')], 1),
           'foo.bar.example.net': ([ipaddress.IPv6Address('5678::4'),
                                    ipaddress.IPv6Address('5678::5')], 4),
           'foo.example.com': ([ipaddress.IPv6Address('5678::2')], 2),
           'bar.example.org': ([ipaddress.IPv6Address('2345::6'),
                                ipaddress.IPv6Address('4567::7')], 6)}
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_all_ipv6s_result=True,
    )
    updater.put_zone_ipv6s('', arg)
    assert updater.put_all_ipv6s_calls == [arg]


def test_put_all_ipv6s_not_implemented(empty_addrfile, data_dir):
    """Test put_zone_ipv6s raises NotImplementedError when put_all_ipv6s
    is not implemented"""
    arg = {'example.com': ([ipaddress.IPv6Address('5678::1')], 1),
           'foo.bar.example.net': ([ipaddress.IPv6Address('5678::4'),
                                    ipaddress.IPv6Address('5678::5')], 4),
           'foo.example.com': ([ipaddress.IPv6Address('5678::2')], 2),
           'bar.example.org': ([ipaddress.IPv6Address('2345::6'),
                                ipaddress.IPv6Address('4567::7')], 6)}
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.put_zone_ipv6s('', arg)
    assert updater.put_all_ipv6s_calls == [arg]


def test_put_all_ipv6s_publish_error(empty_addrfile, data_dir):
    """Test put_zone_ipv6s raises PublishError when put_all_ipv6s does"""
    arg = {'example.com': ([ipaddress.IPv6Address('5678::1')], 1),
           'foo.bar.example.net': ([ipaddress.IPv6Address('5678::4'),
                                    ipaddress.IPv6Address('5678::5')], 4),
           'foo.example.com': ([ipaddress.IPv6Address('5678::2')], 2),
           'bar.example.org': ([ipaddress.IPv6Address('2345::6'),
                                ipaddress.IPv6Address('4567::7')], 6)}
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_all_ipv6s_result=PublishError,
    )
    with pytest.raises(PublishError):
        updater.put_zone_ipv6s('', arg)
    assert updater.put_all_ipv6s_calls == [arg]


def test_put_domain_ipv6s(empty_addrfile, data_dir):
    """Test put_subdomain_ipv6s calls put_domain_ipv6s"""
    addresses = [ipaddress.IPv6Address('5678::2')]
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_domain_ipv6s_result={'example.com': None},
    )
    updater.put_subdomain_ipv6s('example.com', '', addresses, 2)
    assert updater.put_domain_ipv6s_calls == [('example.com', addresses, 2)]


def test_put_domain_ipv6s_not_implemented(empty_addrfile, data_dir):
    """Test put_subdomain_ipv6s raises NotImplementedError when
    put_domain_ipv6s is not implemented"""
    addresses = [ipaddress.IPv6Address('5678::2')]
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
    )
    with pytest.raises(NotImplementedError):
        updater.put_subdomain_ipv6s('example.com', '', addresses, 2)
    assert updater.put_domain_ipv6s_calls == [('example.com', addresses, 2)]


def test_put_domain_ipv6s_publish_error(empty_addrfile, data_dir):
    """Test put_subdomain_ipv6s raises PublishError when put_domain_ipv6s
    does"""
    addresses = [ipaddress.IPv6Address('5678::2')]
    updater = doubles.MockTwoWayUpdater(
        'test_updater', empty_addrfile, data_dir,
        put_domain_ipv6s_result={'example.com': PublishError},
    )
    with pytest.raises(PublishError):
        updater.put_subdomain_ipv6s('example.com', '', addresses, 2)
    assert updater.put_domain_ipv6s_calls == [('example.com', addresses, 2)]
