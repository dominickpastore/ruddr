# TODO remove when done
"""
BaseUpdater
- Has basic members like name, log, addrfile
- Abstract methods initial_update, update_ipv4, update_ipv6
- Static method replace_ipv6_prefix
- Can have methods marked @Retry
"""

# TODO Test basic vars ...
# TODO Test replace_ipv6_prefix ...
# TODO Test @Retry and self.halt by creating an updater with a custom @Retry
#  method (including all combos of intervals) ...

"""
Updater
- Abstract methods publish_ipv4, publish_ipv6
- Does an initial update (which should retry if necessary)
- Retry logic for regular updates
- Note at top of test file for this class that retry logic is tested thoroughly
  in test_baseupdater.py
"""

# TODO Test initial update updates ipv4 if not current and updates addrfile
# TODO Test initial update updates ipv6 if not current and updates addrfile
# TODO Test initial update retries ipv4 on failure (even when ipv6 succeeds)
#  and marks failure in addrfile
# TODO Test initial update retries ipv6 on failure (even when ipv4 succeeds)
#  and marks failure in addrfile
# TODO Test initial update stops retrying both on fatal error after IPv4
#  and marks failure in addrfile
# TODO Test initial update stops retrying both on fatal error after IPv6
#  and marks failure in addrfile

# TODO Test update_ipv4 succeeds, invalidating old address in addrfile first,
#  updating addrfile after
# TODO Test update_ipv6 succeeds, invalidating old address in addrfile first,
#  updating addrfile after
# TODO Test update_ipv4 does nothing when given None, but stops trying to
#  retry
# TODO Test update_ipv6 does nothing when given None, but stops trying to
#  retry
# TODO Test update_ipv4 does nothing when given same address as addrfile
# TODO Test update_ipv6 does nothing when given same address as addrfile
# TODO Test update_ipv4 does nothing when publish_ipv4 not implemented
# TODO Test update_ipv6 does nothing when publish_ipv6 not implemented
# TODO Test update_ipv4 retries after failure, even when IPv6 succeeds, and
#  invalidates old address until succeeding, at which point it stops retrying
#  and updates addrfile
# TODO Test update_ipv6 retries after failure, even when IPv4 succeeds, and
#  invalidates old address until succeeding, at which point it stops retrying
#  and updates addrfile
# TODO Test update_ipv4 and update_ipv6 stops retrying on fatal error during
#  update_ipv4
# TODO Test update_ipv4 and update_ipv6 stops retrying on fatal error during
#  update_ipv6

"""
TwoWayZoneUpdater
- init_hosts_and_zones, as str and structured
- publish_ipv4
- publish_ipv6
- subdomain_of
- fqdn_of
"""
# TODO Test publish_ipv4 with all the variations of method availability ...
# TODO Test publish_ipv6 with all the variations of method availability ...
# TODO Test init_hosts_and_zones with structured hosts, and do an IPv6 update
#  to confirm it works (all others tests will use string hosts)
# TODO Test subdomain_of ...
# TODO Test fqdn_of ...

"""
TwoWayUpdater
- init_hosts, as str and list
- Implements the TwoWayZoneUpdater methods as thin wrappers
"""
# TODO after TwoWayZoneUpdater
# TODO mostly thin wrapper over TwoWayZoneUpdater abstract methods. Call the
#  abstract methods and verify that this class's abstract methods are called
#  appropriately. ...

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