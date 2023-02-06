import pytest

import ruddr

# Publish IPv4:
# - Organize hosts into zones
#   - Hosts with hardcoded zone are in that zone
#   - For others, first try fetching zone
#   - If not implemented, use public suffix list
# - For each zone:
#   - Fetch A records for zone
#     - First try fetching entire zone
#     - If not implemented, fetch records for individual hosts
#   - Replace records for specified hosts, if they exist (error if no existing
#     record, but not if multiple existing records)
#   - Write A records for zone


@pytest.fixture(scope='session')
def data_dir(tmp_path):
    return tmp_path / 'data'


# TODO All hosts have hardcoded zones, zones not fetched
# TODO some hosts have hardcoded zones, those are left alone when fetching
#  zones
# TODO get_zones is implemented, but raises PublishError
# TODO get_zones not implemented, PSL is used
# TODO Host does not fit into one of the fetched zones, PublishError
# TODO Host is 'foo.bar.example.com' and zones include 'bar.example.com' and
#  'example.com', actual zone used is 'bar.example.com' no matter the order
# TODO Host is 'bar.example.com' and zones include 'bar.example.com' and
#  'example.com', actual zone used is 'bar.example.com' no matter the order
#  (can probably be combined with previous with parameterization)

# TODO fetch_zone_ipv4s implemented, all single records updated, put_zone_ipv4s
#  and put_subdomain_ipv4 implemented, put_zone_ipv4s preferred (and
#  fetch_subdomain_ipv4s implemented too but not preferred)
# TODO fetch_zone_ipv4s implemented, extra records left alone
# TODO fetch_zone_ipv4s implemented, missing record is PublishError, other
#  zones and other records still updated
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
