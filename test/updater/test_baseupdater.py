import ipaddress
import logging

import pytest

import ruddr
from ruddr import FatalPublishError, PublishError


def test_member_vars(updater_factory, empty_addrfile):
    """Test BaseUpdater has basic member variables name, log, and addrfile"""
    updater = updater_factory(addrfile=empty_addrfile)
    assert updater.name == "mock_updater_1"
    assert isinstance(updater.log, logging.Logger)
    assert updater.log.name == f"ruddr.updater.{updater.name}"
    assert updater.addrfile is empty_addrfile

@pytest.mark.parametrize('sequence', [
    # (Error|None, 'new'|'repeat'|'retry', delay until next)
    # Error ignored for repeat calls
    # Last delay must extend until any pending retries expire

    # 0: Single successful call
    [(None, 'new', 1)],
    # 1: Two successful calls
    [(None, 'new', 1),
     (None, 'new', 0)],
    # 2: Fail, retry succeeds
    [(PublishError, 'new', 300),
     (None, 'retry', 0)],
    # 3: Fail, new call before retry
    [(PublishError, 'new', 100),
     (None, 'new', 200)],
    # 4: Fail, retry fail, success
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (None, 'retry', 0)],
    # 5: Fail, retry fail, repeat call before retry, retry happens as scheduled
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 100),
     (None, 'repeat', 500),
     (None, 'retry', 0)],
    # 6: Fail, retry fail, success, fail, retry after min delay
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (None, 'retry', 0),
     (PublishError, 'new', 300),
     (None, 'retry', 0)],
    # 7: Fail, retry fail, retry fail, new call fail, retry after min delay
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (PublishError, 'retry', 1100),
     (PublishError, 'new', 300),
     (None, 'retry', 0)],
    # 8: Fail, retry fail until max delay hit, retry fail one more time,
    #    success
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (PublishError, 'retry', 1200),
     (PublishError, 'retry', 2400),
     (PublishError, 'retry', 4800),
     (PublishError, 'retry', 9600),
     (PublishError, 'retry', 19200),
     (PublishError, 'retry', 38400),
     (PublishError, 'retry', 76800),
     (PublishError, 'retry', 86400),
     (PublishError, 'retry', 86400),
     (None, 'retry', 0)],
    # 9: Fail, retry fail until max delay hit, retry fail one more time, new
    #    call fail, retry after min delay
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (PublishError, 'retry', 1200),
     (PublishError, 'retry', 2400),
     (PublishError, 'retry', 4800),
     (PublishError, 'retry', 9600),
     (PublishError, 'retry', 19200),
     (PublishError, 'retry', 38400),
     (PublishError, 'retry', 76800),
     (PublishError, 'retry', 86400),
     (PublishError, 'retry', 86300),
     (PublishError, 'new', 300),
     (None, 'retry', 0)],
    # 10: Fatal right away
    [(FatalPublishError, 'new', 0)],
    # 11: Success, fatal
    [(None, 'new', 1),
     (FatalPublishError, 'new', 0)],
    # 12: Fail, retry fail, retry fail, fatal
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (PublishError, 'retry', 1200),
     (FatalPublishError, 'retry', 0)],
    # 13: Fail, retry fail, retry fail, new call fatal
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (PublishError, 'retry', 1100),
     (FatalPublishError, 'new', 100)],
    # 14: Fail, retry fail until max delay hit, retry fail one more time, fatal
    [(PublishError, 'new', 300),
     (PublishError, 'retry', 600),
     (PublishError, 'retry', 1200),
     (PublishError, 'retry', 2400),
     (PublishError, 'retry', 4800),
     (PublishError, 'retry', 9600),
     (PublishError, 'retry', 19200),
     (PublishError, 'retry', 38400),
     (PublishError, 'retry', 76800),
     (PublishError, 'retry', 86400),
     (PublishError, 'retry', 86400),
     (FatalPublishError, 'retry', 0)],
])
def test_retry(sequence, updater_factory, advance):
    err_sequence = [x[0] for x in sequence]
    updater = updater_factory(err_sequence=err_sequence)

    # Check retry sequence
    arg = 0
    expected_seq = []
    expect_retry = False
    halted = False
    for err, kind, delay in sequence:
        # kind 'new' = new call with new param
        # kind 'repeat' = new call with same param (ignored)
        # kind 'retry' = automatic retry
        if kind == 'new':
            arg += 1
            updater.retry_test(arg)
            expected_seq.append(arg)
        elif kind == 'repeat':
            updater.retry_test(arg)
        elif expect_retry:
            expected_seq.append(arg)

        assert updater.retry_sequence == expected_seq

        if kind != 'repeat':
            expect_retry = err is not None
        advance.by(delay)
        if isinstance(err, FatalPublishError):
            halted = True

    if halted:
        assert updater.halt
    assert updater.retry_sequence == expected_seq
    # No more retries
    assert advance.count_running() == 0


@pytest.mark.parametrize(('network', 'address', 'expected'), [
    (ipaddress.IPv6Network('::/128'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1'),
     ipaddress.IPv6Address('::')),
    (ipaddress.IPv6Network('::2/128'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1'),
     ipaddress.IPv6Address('::2')),
    (ipaddress.IPv6Network('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff/128'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1'),
     ipaddress.IPv6Address('ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')),
    (ipaddress.IPv6Network('2222::/64'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1'),
     ipaddress.IPv6Address('2222::1:1:1:1')),
    (ipaddress.IPv6Network('::/64'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1'),
     ipaddress.IPv6Address('::1:1:1:1')),
    (ipaddress.IPv6Network('ffff:ffff:ffff:ffff::/64'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1'),
     ipaddress.IPv6Address('ffff:ffff:ffff:ffff:1:1:1:1')),
    (ipaddress.IPv6Network('::/0'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1'),
     ipaddress.IPv6Address('1:1:1:1:1:1:1:1')),
])
def test_replace_ipv6_prefix(network, address, expected):
    assert ruddr.updaters.BaseUpdater.replace_ipv6_prefix(
        network, address
    ) == expected
