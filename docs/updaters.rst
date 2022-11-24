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
    hosts = foo bar
    dns_query = .dynu.com@ns1.dynu.com
    ipv6_dialect = separate

**Sample config for NoIP**::

    [updater.main]
    type = standard
    endpoint = http://dynupdate.no-ip.com
    username = <your-username>
    password = <your-password>
    hosts = foo.example.com bar.example.com
    dns_query = .@ns1.no-ip.com
    ipv6_dialect = combined

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
    hosts = foo bar/::1a2b:3c3d
    #dns_query = .example.com[@ns.example.com]
    #ipv6_dialect = separate

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
    A whitespace-separated list of hostnames to keep updated. Note that there
    are two formats you can use when specifying a hostname. First is the
    hostname alone, and the second is the hostname with an IPv6 address.

    When Ruddr does an IPv6 update, it only changes the network prefix portion
    of the address (unless you specified your prefix length as 128, i.e. the
    entire address, in your notifier config). Therefore, Ruddr needs to know
    what to use for the host portion of the address.

    If you specify an IPv6 address along with a hostname, Ruddr will get the
    host portion that way (it ignores the network prefix of the address).
    Otherwise, Ruddr will use the ``dns_query`` configuration (see below) to
    look up the current IPv6 address using DNS.

    Allowing Ruddr to look up the IPv6 address with DNS is recommended for
    convenience.

``dns_query``
    This option is required when any hostname in ``hosts`` does not have an
    IPv6 address provided with it. It provides the additional info Ruddr needs
    to fetch the current address from DNS. The format is
    ``<.domain>[@server]``.

    The ``<.domain>`` portion is the rest of the domain name to append to each
    hostname when doing a DNS lookup. The optional ``@server`` portion lets
    you specify a specific DNS server to use (for example, you can provide the
    nameserver for your DDNS provider to look up the record from them
    directly).

    For example: If you have hostname "example" with Dynu, you can use this
    configuration to have Ruddr do the lookup as "example.dynu.com" on one of
    Dynu's own nameservers::

        hosts = example
        dns_query = .dynu.com@ns1.dynu.com

    In another case, you may want to have Ruddr get the host portion of the
    IPv6 from your LAN's internal DNS server at 192.168.0.1, and perhaps the
    hostname alone is enough to do the lookup there. Use a single dot as the
    domain portion to say the hostname is lookup-able as-is::

        hosts = example
        dns_query = .@192.168.0.1

    (Note that some networks may appear to allow bare hostname lookups, when in
    fact the OS is automatically appending your network's local domain name.)

    .. note::
       Some providers may require you to specify fully-qualified domain names
       as the ``hosts`` to be updated. In that case, use a single dot as the
       domain portion in ``dns_query`` since no additional domain needs to be
       added for lookups.

``ipv6_dialect``
    The DynDNS API was originally designed for IPv4 only. As a result,
    different providers added IPv6 support in different ways. This option lets
    you specify how the updater should provide an IPv6 address to your
    provider. These are the possibilities:

    ``separate`` provides IPv6 addresses using a separate ``myipv6`` parameter
    in the URL. This is the default.

    ``combined`` provides both IP addresses together in the ``myip`` parameter,
    separated by a comma, e.g. ``myip=1.2.3.4,2001:0db8::4``

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
    for. Multiple domain names should be separated by whitespace (note: if
    using newlines as a separator, lines after the first must be indented).
    These may be your root domains (e.g. example.com), subdomains (e.g.
    www.example.com), or any mixture of both.

``endpoint``
    The API endpoint to use, that is, the base URL for the LiveDNS API. This
    should rarely need to be set explicitly, as it defaults to Gandi's
    production LiveDNS API endpoint. (Gandi does not currently provide a
    staging API environment as of September 16, 2021, but if they do in the
    future, this option could be used to switch to that for testing purposes.)

HE Updaters
-----------

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
