"""Tests for Addrfile"""
import ipaddress

import pytest

import doubles
import ruddr.addrfile


@pytest.fixture
def addrfile_factory(tmp_path):
    count = 0

    def factory(contents: str):
        nonlocal count
        count += 1
        path = tmp_path / f"addrfile_{count}"

        with open(path, "w") as f:
            for line in contents.splitlines():
                print(line.strip(), file=f)

        return ruddr.addrfile.Addrfile(path)
    return factory


def test_new_addrfile(empty_addrfile):
    """Test new, nonexistent addrfile can get and set addresses"""
    assert empty_addrfile.get_ipv4("test") == (None, False)
    assert empty_addrfile.get_ipv6("test") == (None, False)
    assert empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )

    empty_addrfile.set_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))
    empty_addrfile.set_ipv6("test", ipaddress.IPv6Network('1234::/64'))
    assert (empty_addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (empty_addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )

    empty_addrfile.set_ipv4("test2", ipaddress.IPv4Address('1.2.3.4'))
    empty_addrfile.set_ipv6("test2", ipaddress.IPv6Network('1234::/64'))
    assert (empty_addrfile.get_ipv4("test2") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (empty_addrfile.get_ipv6("test2") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not empty_addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not empty_addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('1234::/64')
    )
    assert empty_addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('5.6.7.8')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('5678::/64')
    )


def test_existing_addrfile(empty_addrfile):
    """Test getting addresses from existing addrfile"""
    empty_addrfile.set_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))
    empty_addrfile.set_ipv6("test", ipaddress.IPv6Network('1234::/64'))
    empty_addrfile.invalidate_ipv4("test2", ipaddress.IPv4Address('5.6.7.8'))
    empty_addrfile.invalidate_ipv6("test2", ipaddress.IPv6Network('5678::/64'))
    path = empty_addrfile.path

    addrfile = ruddr.addrfile.Addrfile(path)
    assert (addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )
    addrfile.invalidate_ipv4("test", ipaddress.IPv4Address('2.3.4.5'))
    addrfile.invalidate_ipv6("test", ipaddress.IPv6Network('2345::/64'))
    assert (addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('2.3.4.5'), False))
    assert (addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('2345::/64'), False))
    assert addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('2.3.4.5')
    )
    assert addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('2345::/64')
    )

    assert (addrfile.get_ipv4("test2") ==
            (ipaddress.IPv4Address('5.6.7.8'), False))
    assert (addrfile.get_ipv6("test2") ==
            (ipaddress.IPv6Network('5678::/64'), False))
    assert addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('5678::/64')
    )
    assert addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('1.2.3.4')
    )
    assert addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('1234::/64')
    )
    addrfile.set_ipv4("test2", ipaddress.IPv4Address('6.7.8.9'))
    addrfile.set_ipv6("test2", ipaddress.IPv6Network('6789::/64'))
    assert (addrfile.get_ipv4("test2") ==
            (ipaddress.IPv4Address('6.7.8.9'), True))
    assert (addrfile.get_ipv6("test2") ==
            (ipaddress.IPv6Network('6789::/64'), True))
    assert not addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('6.7.8.9')
    )
    assert not addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('6789::/64')
    )


def test_only_ipv4_is_set(empty_addrfile):
    """Test getting addresses when only IPv4 is set"""
    empty_addrfile.set_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))
    empty_addrfile.invalidate_ipv4("test2", ipaddress.IPv4Address('5.6.7.8'))
    path = empty_addrfile.path

    addrfile = ruddr.addrfile.Addrfile(path)
    assert (addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert addrfile.get_ipv6("test") == (None, False)
    assert not empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )

    assert (addrfile.get_ipv4("test2") ==
            (ipaddress.IPv4Address('5.6.7.8'), False))
    assert addrfile.get_ipv6("test2") == (None, False)
    assert empty_addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('5.6.7.8')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('5678::/64')
    )
    assert empty_addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('1.2.3.4')
    )


def test_only_ipv6_is_set(empty_addrfile):
    """Test getting addresses when only IPv6 is set"""
    empty_addrfile.set_ipv6("test", ipaddress.IPv6Network('1234::/64'))
    empty_addrfile.invalidate_ipv6("test2", ipaddress.IPv6Network('5678::/64'))
    path = empty_addrfile.path

    addrfile = ruddr.addrfile.Addrfile(path)
    assert addrfile.get_ipv4("test") == (None, False)
    assert (addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )

    assert addrfile.get_ipv4("test2") == (None, False)
    assert (addrfile.get_ipv6("test2") ==
            (ipaddress.IPv6Network('5678::/64'), False))
    assert empty_addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('5.6.7.8')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('5678::/64')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('1234::/64')
    )


def test_set_ipv4_invalidate_ipv6(empty_addrfile):
    """Test getting addresses when IPv4 is set successfully and IPv6 is
    invalidated"""
    empty_addrfile.set_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))
    empty_addrfile.invalidate_ipv6("test", ipaddress.IPv6Network('1234::/64'))
    path = empty_addrfile.path

    addrfile = ruddr.addrfile.Addrfile(path)
    assert (addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), False))
    assert not empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )


def test_set_ipv6_invalidate_ipv4(empty_addrfile):
    """Test getting addresses when IPv6 is set successfully and IPv4 is
    invalidated"""
    empty_addrfile.invalidate_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))
    empty_addrfile.set_ipv6("test", ipaddress.IPv6Network('1234::/64'))
    path = empty_addrfile.path

    addrfile = ruddr.addrfile.Addrfile(path)
    assert (addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), False))
    assert (addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert empty_addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert empty_addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )


def test_read_error(mocker, tmp_path):
    """Test read error in addrfile"""
    mocker.patch('builtins.open', return_value=doubles.BrokenFile())
    addrfile = ruddr.addrfile.Addrfile(tmp_path / 'addrfile')

    assert addrfile.get_ipv4("test") == (None, False)
    assert addrfile.get_ipv6("test") == (None, False)
    assert addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )


def test_set_ipv4_write_error(mocker, tmp_path):
    """Test write errors for set_ipv4"""
    mocker.patch('builtins.open',
                 return_value=doubles.BrokenFile(write_broken=True))
    addrfile = ruddr.addrfile.Addrfile(tmp_path / 'addrfile')
    with pytest.raises(OSError):
        addrfile.set_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))


def test_set_ipv6_write_error(mocker, tmp_path):
    """Test write errors for set_ipv6"""
    mocker.patch('builtins.open',
                 return_value=doubles.BrokenFile(write_broken=True))
    addrfile = ruddr.addrfile.Addrfile(tmp_path / 'addrfile')
    with pytest.raises(OSError):
        addrfile.set_ipv6("test", ipaddress.IPv6Network('1234::/64'))


def test_invalidate_ipv4_write_error(mocker, tmp_path):
    """Test write errors for invalidate_ipv4"""
    mocker.patch('builtins.open',
                 return_value=doubles.BrokenFile(write_broken=True))
    addrfile = ruddr.addrfile.Addrfile(tmp_path / 'addrfile')
    with pytest.raises(OSError):
        addrfile.invalidate_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))


def test_invalidate_ipv6_write_error(mocker, tmp_path):
    """Test write errors for invalidate_ipv6"""
    mocker.patch('builtins.open',
                 return_value=doubles.BrokenFile(write_broken=True))
    addrfile = ruddr.addrfile.Addrfile(tmp_path / 'addrfile')
    with pytest.raises(OSError):
        addrfile.invalidate_ipv6("test", ipaddress.IPv6Network('1234::/64'))


@pytest.mark.parametrize('contents', [
    '',
    '["1.2.3.4"]',
    '{}',
    '1',
    'true',
    'false',
    'null',
    '"1.2.3.4"',
    'invalid json',
])
def test_not_filled_json_object(addrfile_factory, contents):
    """Test reading an addrfile that's not JSON, a JSON non-object type, or is
    an empty JSON object"""
    addrfile = addrfile_factory(contents)
    assert addrfile.get_ipv4("test") == (None, False)
    assert addrfile.get_ipv6("test") == (None, False)
    assert addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )

    addrfile.set_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))
    addrfile.set_ipv6("test", ipaddress.IPv6Network('1234::/64'))
    assert (addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )

    addrfile2 = ruddr.addrfile.Addrfile(addrfile.path)
    assert (addrfile2.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile2.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not addrfile2.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not addrfile2.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert addrfile2.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile2.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )


@pytest.mark.parametrize('contents', [
    """{
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": null,
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": true,
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": false,
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": 1,
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": "1.2.3.4",
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": ["1.2.3.4"],
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv5": ["1.2.3.4", true]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true],
            "ipv5": ["1.2.3.4", true]
        },
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {
            "ipv4": ["1234::/64", true],
            "ipv6": ["1234::/64", true]
        },
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1.2.3.4", true]
        },
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4"]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4", true, null]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4", 1]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4", null]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4", "true"]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4", [true]]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4", {}]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": [["1.2.3.4"], true]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": [{}, true]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": [1234, true]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": [true, true]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": ["1.2.3.4.5", true]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": [["1.2.3.4", true]]},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": {"1.2.3.4": true}},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": "1.2.3.4"},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": null},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": true},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": false},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
    """{
        "test": {"ipv4": 1234},
        "test2": {
            "ipv4": ["1.2.3.4", true],
            "ipv6": ["1234::/64", true]
        }
    }""",
])
def test_one_invalid_key(addrfile_factory, contents):
    """Test reading an addrfile with one malformed/missing key and one valid
    key"""
    addrfile = addrfile_factory(contents)

    assert addrfile.get_ipv4("test") == (None, False)
    assert addrfile.get_ipv6("test") == (None, False)
    assert addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )

    assert (addrfile.get_ipv4("test2") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile.get_ipv6("test2") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('1234::/64')
    )
    assert addrfile.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('5678::/64')
    )

    addrfile.set_ipv4("test", ipaddress.IPv4Address('1.2.3.4'))
    addrfile.set_ipv6("test", ipaddress.IPv6Network('1234::/64'))
    assert (addrfile.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert addrfile.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )

    addrfile2 = ruddr.addrfile.Addrfile(addrfile.path)

    assert (addrfile2.get_ipv4("test") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile2.get_ipv6("test") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not addrfile2.needs_ipv4_update(
        "test", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not addrfile2.needs_ipv6_update(
        "test", ipaddress.IPv6Network('1234::/64')
    )
    assert addrfile2.needs_ipv4_update(
        "test", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile2.needs_ipv6_update(
        "test", ipaddress.IPv6Network('5678::/64')
    )

    assert (addrfile2.get_ipv4("test2") ==
            (ipaddress.IPv4Address('1.2.3.4'), True))
    assert (addrfile2.get_ipv6("test2") ==
            (ipaddress.IPv6Network('1234::/64'), True))
    assert not addrfile2.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('1.2.3.4')
    )
    assert not addrfile2.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('1234::/64')
    )
    assert addrfile2.needs_ipv4_update(
        "test2", ipaddress.IPv4Address('5.6.7.8')
    )
    assert addrfile2.needs_ipv6_update(
        "test2", ipaddress.IPv6Network('5678::/64')
    )
