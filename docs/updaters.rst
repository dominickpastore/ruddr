Updaters
========

Updaters are the modules in Ruddr that interface with your dynamic DNS
provider. Different providers use different protocols and APIs, which
correspond with the various updater types available.

Sample configurations are provided for some popular DDNS providers. However, if
none of the built-in updaters below are compatible with your provider, you can
write your own. (see :ref:`updater_dev`).

Standard Updater
----------------

Type: ``standard``

This updater is compatible with a wide variety of providers that mimic an API
first introduced by DynDNS (dyn.com, now owned by Oracle). Despite the
updater's name, the API is not officially standardized. However, it has
effectively become a de facto standard. If your provider supports updates via a
URL that looks like ``http[s]://<hostname>/nic/update?myip=<IP address>`` or
``http[s]://<username>:<password>@<hostname>/nic/update?myip=<IP address>``,
this is the updater to use.

**Sample config for Dynu**::

    [updater.main]
    type = standard
    endpoint = https://api.dynu.com
    username = <your-username>
    password = <your-password>
    hosts = foo.dynuddns.com/foo.dynuddns.com bar.dynuddns.com/::1a2b:3c3d
    nameserver = ns1.dynu.com
    ipv6_dialect = separate_no
    min_retry_interval = 600

**Sample config for NoIP**::

    [updater.main]
    type = standard
    endpoint = http://dynupdate.no-ip.com
    username = <your-username>
    password = <your-password>
    hosts = foo.ddns.net/foo.ddns.net bar.ddns.net/::1a2b:3c3d
    nameserver = ns1.no-ip.com
    ipv6_dialect = combined
    min_retry_interval = 1800

.. TODO Give sample configs for other major providers

**General sample config**:

This config snippet shows all the options available for this updater. If your
provider isn't listed above, but does use an update URL that looks like
``http[s]://<hostname>/nic/update?myip=<IP address>`` or
``http[s]://<username>:<password>@<hostname>/nic/update?myip=<IP address>``,
there's a good chance you can create a working config using these options.

.. TODO Note about how to send documentation updates

::

    [updater.main]
    type = standard
    endpoint = https://update.example.com
    username = <your-username>
    password = <your-password>
    hosts = foo/foo.example.com bar/::1a2b:3c3d
    #nameserver = ns.example.com
    #ipv6_dialect = separate
    #min_retry_interval = 300

**Configuration options:**

``endpoint``
    The schema and hostname part of your provider's update URL, that is, the
    part before ``/nic/update?...``. Do not include a slash at the end and do
    not include a username or password.

``username``
    The username to include with update requests

``password``
    The password to include with update requests

``hosts``
    A whitespace-separated list of hostnames to keep updated. Each entry must
    be in one of the following three formats:

    ``<hostname>/-`` Ruddr requires an existing IPv6 address in order to do
    IPv6 updates, since it only changes the network prefix for IPv6 addresses.
    However, if you do not need IPv6 addresses, you can use this format, and
    the updater will ignore IPv6 addresses from the notifier.

    ``<hostname>/<IPv6-address>`` For IPv6 updates, Ruddr will take the given
    address, replace its network prefix with the one from the notifier, and
    publish the resulting address.

    ``<hostname>/<fqdn>`` For IPv6 updates, Ruddr will look up the given
    fully-qualified domain name to get an IPv6 address from an AAAA record. It
    will take that address, replace the network prefix with the one from the
    notifier, and publish the resulting address. **This is the recommended
    format, since it will update the prefix of the address already in DNS.**

``nameserver``
    This option is used only if you used the ``<hostname>/<fqdn>`` format
    for any of the entries in ``hosts``. It allows you to specify a specific
    nameserver to query. You can specify your provider's nameserver here to
    ensure Ruddr gets the most up-to-date result directly from them.

``ipv6_dialect``
    The DynDNS API was originally designed for IPv4 only. As a result,
    different providers added IPv6 support in different ways. This option lets
    you specify how the updater should provide an IPv6 address to your
    provider. These are the possibilities:

    ``separate`` provides IPv6 addresses using a separate ``myipv6`` parameter
    in the URL. If only one address needs to be set (IPv4 or IPv6), the
    parameter for the other type of address will be omitted. This is the
    default.

    ``separate_no`` is like ``separate``, except if only one address can be
    set, ``no`` is sent in place of the other address.

    ``combined`` provides both IP addresses together in the ``myip`` parameter,
    separated by a comma, e.g. ``myip=1.2.3.4,2001:0db8::4``. If only one
    address needs to be set (IPv4 or IPv6), it will be sent in the ``myip``
    parameter alone, without a comma.

``min_retry_interval``
    The minimum number of seconds to wait between retries when an update fails.
    This minimum is used for the first retry, with an exponential backoff for
    subsequent retries. Some providers, especially free ones, have specific
    requirements for this.

FreeDNS Updater
---------------

Type: ``freedns``

This updater is for FreeDNS, the dynamic DNS service at freedns.afraid.org.

**Sample config for FreeDNS**::

    [updater.main]
    type = freedns
    username = <freedns-username>
    password = <freedns-password>
    fqdns = foo.example.com bar.example.com

**Configuration options:**

``username``
    Your account's username at freedns.afraid.org

``password``
    Your account's password at freedns.afraid.org

``fqdns``
    A whitespace-separated list of domains or subdomains in your account whose
    IP address(es) should be updated.

Gandi Updater
-------------

Type: ``gandi``

This updater uses Gandi's LiveDNS API to update the A and AAAA records
associated with a domain name. If your domain name is registered with Gandi and
you use their DNS services (marketed as "LiveDNS"), this updater is a great
choice for you.

**Sample config for Gandi (with defaults commented)**::

    [updater.main]
    type = gandi
    api_key = <your-api-key>
    fqdns = example.com www.example.com
    #endpoint = https://api.gandi.net/v5/livedns

**Configuration options:**

``api_key``
    Your production LiveDNS API key. You can generate this by logging in to
    https://account.gandi.net/ and navigating to the "Security" section.

``fqdns``
    A list of fully qualified domain names to update the A and AAAA records
    for. Multiple domain names should be separated by whitespace. These may be
    your root domains (e.g. example.com), subdomains (e.g. www.example.com), or
    any mixture of both.

``endpoint``
    The API endpoint to use, that is, the base URL for the LiveDNS API. This
    should rarely need to be set explicitly, as it defaults to Gandi's
    production LiveDNS API endpoint. (Gandi does not currently provide a
    staging API environment as of September 16, 2021, but if they do in the
    future, this option could be used to switch to that for testing purposes.)

HE Updater
----------

Type: ``he``

This is a niche updater for those who use Hurricane Electric's IPv6 tunnel
broker service. The tunnel broker requires an up-to-date IPv4 address at all
times, and this updater can be used to provide it. Since that is its only
purpose, it ignores any IPv6 addresses supplied by a notifier.

**Sample config for Hurricane Electric's tunnel broker (with defaults
commented)**::

    [updater.main]
    type = gandi
    tunnel = <tunnel-id>
    username = <username>
    password = <password>
    #url = https://ipv4.tunnelbroker.net/nic/update

**Configuration options:**

``tunnel``
    Your Hurricane Electric tunnel ID

``username``
    Your Hurricane Electric username

``password``
    Your Hurricane Electric password

``url``
    The URL to use for updates, if Hurricane Electric's URL should not be used.
    The vast majority of users should not set this.
