"""
OneWayUpdater
- init_params, as str and structured
- publish_ipv4
- publish_ipv6
"""

# TODO Test publish_ipv4 calls publish_ipv4_one_host on all hosts, no matter
#  how they are configured for IPv6
# TODO Test publish_ipv4 calls publish_ipv4_one_host on all hosts even when
#  some (or all) raise PublishError
# TODO Test publish_ipv6 does nothing for hosts without an IPv6 lookup method,
#  but no PublishError
# TODO Test publish_ipv6 calls publish_ipv6_one_host using hardcoded addr
# TODO Test publish_ipv6 calls publish_ipv6_one_host using DNS lookup
# TODO Test publish_ipv6 raises PublishError when DNS lookup server unreachable
# TODO Test publish_ipv6 raises PublishError when DNS lookup has no AAAA record
# TODO Test publish_ipv6 calls publish_ipv6_one_host on remaining hosts even
#  when one has no IPv6 lookup method (parameterized: (none, addr, server),
#  (server, none, addr), (addr, server, none))
# TODO Test publish_ipv4 calls publish_ipv4_one_host on all hosts even when
#  some (or all) raise PublishError

# TODO Test init_params with structured hosts, providing nameserver, and
#  providing retry interval and check that it uses the hosts, nameserver, and
#  retry interval (try an IPv6 update to confirm)
#  (init_params with string hosts, default None nameserver, and default retry
#  interval should be tested by the other tests.)
