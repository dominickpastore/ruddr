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

.. TODO

.. TODO Give sample configs for major providers

.. TODO When developing, allow existing addresses to be fetched either from DNS
   (potentially with a configured server) or to be manually specified

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

.. TODO
