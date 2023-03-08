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

import collections
import ipaddress
import socket

import dns.resolver
import pytest

import doubles
from ruddr import PublishError


@pytest.fixture
def gai_mocker(mocker):
    """Fixture returning a function that mocks socket.getaddrinfo. Useful both
    for system resolver (for most tests) and to inject our own DNS server for
    the custom nameserver test"""
    def do_mock(**kwargs):
        def mock_gai(host, port, **_):
            if port is None:
                port = 0

            if host in kwargs:
                result = []
                for addr in kwargs[host]:
                    try:
                        ipaddress.IPv4Address(addr)
                    except ValueError:
                        af = socket.AF_INET6
                        sockaddr = (addr, port, 0, 0)
                    else:
                        af = socket.AF_INET
                        sockaddr = (addr, port)

                    result.append((af, socket.SOCK_DGRAM, 17, '', sockaddr))
                return result
            else:
                return []
        return mocker.patch('socket.getaddrinfo', side_effect=mock_gai)

    return do_mock


def test_publish_ipv4(empty_addrfile):
    """Test publish_ipv4 calls publish_ipv4_one_host on all hosts, no matter
    how they are configured for IPv6"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/- host2/1:2:3:4:5::6 host3/host3.example.com")
    updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    assert updater.ipv4s_published == collections.Counter([
        ('host1', ipaddress.IPv4Address('5.6.7.8')),
        ('host2', ipaddress.IPv4Address('5.6.7.8')),
        ('host3', ipaddress.IPv4Address('5.6.7.8')),
    ])
    assert updater.ipv6s_published == collections.Counter()


@pytest.mark.parametrize('errors', [
    ['host1'], ['host2'], ['host3'], ['host1', 'host2', 'host3']
])
def test_publish_ipv4_publish_error(errors, empty_addrfile):
    """Test publish_ipv4 calls publish_ipv4_one_host on all hosts, even when
    some or all raise PublishError"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile,
                                        ipv4_errors=errors)
    updater.init_params("host1/- host2/1:2:3:4:5::6 host3/host3.example.com")
    with pytest.raises(PublishError):
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))
    assert updater.ipv4s_published == collections.Counter([
        ('host1', ipaddress.IPv4Address('5.6.7.8')),
        ('host2', ipaddress.IPv4Address('5.6.7.8')),
        ('host3', ipaddress.IPv4Address('5.6.7.8')),
    ])
    assert updater.ipv6s_published == collections.Counter()


def test_publish_ipv6_no_lookup_method(empty_addrfile):
    """Test publish_ipv6 does nothing for hosts without an IPv6 lookup method,
    but doesn't raise PublishError"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/- host2/-")
    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter()


def test_publish_ipv6_hardcoded_addr(empty_addrfile):
    """Test publish_ipv6 calls publish_ipv6_one_host on hosts with a hardcoded
    IPv6 addr"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/1:2:3:4:5::6 host2/::7:8:9:0")
    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter([
        ('host1', ipaddress.IPv6Address('5678::5:0:0:6')),
        ('host2', ipaddress.IPv6Address('5678::7:8:9:0')),
    ])


def test_publish_ipv6_dns_lookup(empty_addrfile, gai_mocker):
    """Test publish_ipv6 calls publish_ipv6_one_host on hosts using DNS
    lookup"""
    mock_gai = gai_mocker(foo=['1:2:3:4:5::6'], bar=['::7:8:9:0'])
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/foo host2/bar")
    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter([
        ('host1', ipaddress.IPv6Address('5678::5:0:0:6')),
        ('host2', ipaddress.IPv6Address('5678::7:8:9:0')),
    ])
    assert mock_gai.call_args_list == [
        (('foo', None), {'family': socket.AF_INET6}),
        (('bar', None), {'family': socket.AF_INET6}),
    ]


def test_publish_ipv6_mix(empty_addrfile, gai_mocker):
    """Test publish_ipv6 calls publish_ipv6_one_host on hosts using a mixture
    of host configurations"""
    mock_gai = gai_mocker(foo=['2600:2:3:4:a::b'], bar=['::c:d:e:f'])
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/- host2/1:2:3:4:5::6 host3/foo "
                        "host4/- host5/::7:8:9:0 host6/bar")
    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter([
        ('host2', ipaddress.IPv6Address('5678::5:0:0:6')),
        ('host3', ipaddress.IPv6Address('5678::a:0:0:b')),
        ('host5', ipaddress.IPv6Address('5678::7:8:9:0')),
        ('host6', ipaddress.IPv6Address('5678::c:d:e:f')),
    ])
    assert mock_gai.call_args_list == [
        (('foo', None), {'family': socket.AF_INET6}),
        (('bar', None), {'family': socket.AF_INET6}),
    ]


@pytest.mark.parametrize('errors', [
    ['host2'], ['host3'], ['host5'], ['host6'],
    ['host1', 'host2', 'host3', 'host4', 'host5', 'host6']
])
def test_publish_ipv6_publish_error(errors, empty_addrfile, gai_mocker):
    """Test publish_ipv6 calls publish_ipv6_one_host on all hosts, even when
    some or all raise PublishError"""
    mock_gai = gai_mocker(foo=['2600:2:3:4:a::b'], bar=['::c:d:e:f'])
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile,
                                        ipv6_errors=errors)
    updater.init_params("host1/- host2/1:2:3:4:5::6 host3/foo "
                        "host4/- host5/::7:8:9:0 host6/bar")
    with pytest.raises(PublishError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter([
        ('host2', ipaddress.IPv6Address('5678::5:0:0:6')),
        ('host3', ipaddress.IPv6Address('5678::a:0:0:b')),
        ('host5', ipaddress.IPv6Address('5678::7:8:9:0')),
        ('host6', ipaddress.IPv6Address('5678::c:d:e:f')),
    ])
    assert mock_gai.call_args_list == [
        (('foo', None), {'family': socket.AF_INET6}),
        (('bar', None), {'family': socket.AF_INET6}),
    ]


def test_publish_ipv6_no_such_host(empty_addrfile):
    """Test publish_ipv6 raises PublishError when DNS lookup on nonexistent
    host"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/nosuchhost.dcpx.org")
    with pytest.raises(PublishError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter()


def test_publish_ipv6_no_such_host_custom_nameserver(empty_addrfile):
    """Test publish_ipv6 raises PublishError when DNS lookup on nonexistent
    host from a custom nameserver"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/nosuchhost.dcpx.org",
                        nameserver="1.1.1.1")
    with pytest.raises(PublishError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter()


def test_publish_ipv6_no_aaaa_record(empty_addrfile):
    """Test publish_ipv6 raises PublishError when DNS lookup returns no AAAA
    record"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/ipv4.icanhazip.com")
    with pytest.raises(PublishError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter()


def test_publish_ipv6_no_aaaa_record_custom_nameserver(empty_addrfile):
    """Test publish_ipv6 raises PublishError when DNS lookup returns no AAAA
    record from a custom nameserver"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/ipv4.icanhazip.com",
                        nameserver="1.1.1.1")
    with pytest.raises(PublishError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter()


def test_publish_ipv6_nameserver_unreachable(empty_addrfile):
    """Test publish_ipv6 raises PublishError when custom DNS nameserver is
    unreachable"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/ipv6.icanhazip.com",
                        nameserver="192.0.2.2")
    with pytest.raises(PublishError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter()


@pytest.mark.parametrize(('addrs', 'expected'), [
    (['fdff:2:3:4:1:1:1:1', '2600:2:3:4:2:2:2:2', '2600:6:7:8:3:3:3:3'],
     '5678::2:2:2:2'),
    (['2600:2:3:4:2:2:2:2', 'fdff:2:3:4:1:1:1:1', '2600:6:7:8:3:3:3:3'],
     '5678::2:2:2:2'),
    (['fe80::1:1:1:1', '2600:2:3:4:2:2:2:2', '2600:6:7:8:3:3:3:3'],
     '5678::2:2:2:2'),
    (['2600:2:3:4:2:2:2:2', 'fe80::1:1:1:1', '2600:6:7:8:3:3:3:3'],
     '5678::2:2:2:2'),
    (['fe80::1:1:1:1', 'fdff:2:3:4:2:2:2:2', 'fdff:6:7:8:3:3:3:3'],
     '5678::2:2:2:2'),
    (['fdff:2:3:4:2:2:2:2', 'fe80::1:1:1:1', 'fdff:6:7:8:3:3:3:3'],
     '5678::2:2:2:2'),
    (['fe80::1:1:1:1', 'fdff:2:3:4:2:2:2:2', '2600:6:7:8:3:3:3:3'],
     '5678::3:3:3:3'),
    (['fdff:2:3:4:2:2:2:2', 'fe80::1:1:1:1', '2600:6:7:8:3:3:3:3'],
     '5678::3:3:3:3'),
    (['2600:2:3:4:2:2:2:2', 'fe80::1:1:1:1', 'fdff:6:7:8:3:3:3:3'],
     '5678::2:2:2:2'),
    (['fe80::1:1:1:1', 'fe80::2:2:2:2'],
     '5678::1:1:1:1'),
])
def test_publish_ipv6_address_precendence(addrs, expected,
                                          empty_addrfile, gai_mocker):
    """Test publish_ipv6 prefers using a global unicast IPv6 over a private
    IPv6 over a link-local IPv6 if multiple are available, but will use the
    first available"""
    mock_gai = gai_mocker(foo=addrs)
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params("host1/foo")
    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert updater.ipv4s_published == collections.Counter()
    assert updater.ipv6s_published == collections.Counter([
        ('host1', ipaddress.IPv6Address(expected)),
    ])
    assert mock_gai.call_args_list == [
        (('foo', None), {'family': socket.AF_INET6}),
    ]


def test_publish_ipv4_not_implemented(empty_addrfile):
    """Test publish_ipv4 raises NotImplementedError when publish_ipv4_one_host
    does"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile,
                                        ipv4_implemented=False)
    updater.init_params("host1/- host2/1:2:3:4:5::6 host3/- host4/a::b")
    with pytest.raises(NotImplementedError):
        updater.publish_ipv4(ipaddress.IPv4Address('5.6.7.8'))


def test_publish_ipv6_not_implemented(empty_addrfile):
    """Test publish_ipv6 raises NotImplementedError when publish_ipv6_one_host
    does"""
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile,
                                        ipv6_implemented=False)
    updater.init_params("host1/- host2/1:2:3:4:5::6 host3/- host4/a::b")
    with pytest.raises(NotImplementedError):
        updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))


def test_init_params_structured(empty_addrfile, gai_mocker, mocker):
    """Test init_params with structured input instead of raw string and also
    check that it uses a custom nameserver and retry interval"""
    mock_gai = gai_mocker(foo=['1.1.1.1'])
    resolve = mocker.spy(dns.resolver.Resolver, 'resolve')
    updater = doubles.MockOneWayUpdater('test_updater', empty_addrfile)
    updater.init_params(
        [
            ('host1', None),
            ('host2', ipaddress.IPv6Address('1:2:3:4:5::6')),
            ('host3', 'ipv6.icanhazip.com'),
            ('host4', None),
            ('host5', ipaddress.IPv6Address('::7:8:9:0')),
        ],
        nameserver='foo',
        min_retry=1800,
    )
    assert updater.min_retry_interval == 1800

    updater.publish_ipv6(ipaddress.IPv6Network('5678::/64'))
    assert mock_gai.call_args_list == [
        (('foo', 53), {'type': socket.SOCK_DGRAM}),
    ]
    resolve.assert_called_once_with(mocker.ANY, 'ipv6.icanhazip.com', 'AAAA')
    assert updater.ipv4s_published == collections.Counter()
    assert len(updater.ipv6s_published) == 3
    assert (('host2', ipaddress.IPv6Address('5678::5:0:0:6')) in
            updater.ipv6s_published)
    assert (('host5', ipaddress.IPv6Address('5678::7:8:9:0')) in
            updater.ipv6s_published)
