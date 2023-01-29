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
# TODO Test update_ipv4 when given same address as last update after failure
# TODO Test update_ipv6 when given same address as last update after failure
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
#
# TODO Test update_ipv4 stops retrying (fatal error) when addrfile write error
# TODO Test update_ipv6 stops retrying (fatal error) when addrfile write error
