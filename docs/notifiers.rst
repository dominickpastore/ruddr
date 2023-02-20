Notifiers
=========

Notifiers monitor the current public IP address and "notify" when it changes.
Since there are different ways to do this, there are a variety of notifier
types built into Ruddr. They are described below, along with their
configuration options and sample configurations. (Note that some configuration
options apply to all notifier types. Those options are described at
:ref:`notifier_config` on the previous page.)

If none of the built-in notifiers below meet your needs, Ruddr can be extended
with notifiers from PyPI, or you can write your own (see :ref:`notifier_dev`).

IFace Notifier
--------------

Type: ``iface``

An iface notifier periodically checks the IP address of an attached network
interface. This is a good choice when Ruddr is running on your router itself.

**Sample config (with defaults commented)**::

    [notifier.main]
    type = iface
    iface = eth0
    #ipv6_prefix = 64
    #interval = 1800
    #retry_min_interval = 10
    #retry_max_interval = 600
    #allow_private = no

**Configuration options:**

``iface``
   The network interface whose address should be checked.

``ipv6_prefix``
   Number of bits that make up the network prefix of the IPv6 address. This is
   the part of the IPv6 address Ruddr will monitor for changes, and the part
   that will be updated by any attached updaters. The bits after the prefix are
   ignored. The default is 64, but note that many ISPs will delegate a larger
   block of addresses (often an entire 56-bit prefix). You should check what
   prefix size your ISP delegates. Note that this only applies to IPv6
   addresses; Ruddr always monitors and updates entire IPv4 addresses.

``interval``
   The number of seconds between IP address checks under normal conditions.

``retry_min_interval``
   If an IP address check fails (i.e. IPv4 address is not available when
   ``ipv4_required`` is true or IPv6 address is not available when
   ``ipv6_required`` is true), the notifier goes into retry mode with
   exponential backoff. The first retry will occur ``retry_min_interval``
   seconds later. The interval will double for each subsequent retry until
   a retry fully succeeds or ``retry_max_interval`` is reached.

``retry_max_interval``
   When the retry interval reaches this duration in seconds, it remains
   constant until a retry succeeds. See ``retry_min_interval`` for more
   explanation.

``allow_private``
   The notifier always ignores link-local (sometimes called APIPA) IPv4 and
   IPv6 addresses (169.254.0.0/16, fe80::/10). By default, it also ignores
   private network addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
   fd00::/8), but if this option is true/on/yes/1, it does not.

Systemd Notifier
----------------

Type: ``systemd``

A systemd notifier is *very* similar to an iface notifier, with just one
additional feature: It ties in to systemd-networkd via DBus to immediately
detect when interfaces go up or down, and does an additional notify at that
point. On systems where systemd-networkd manages the network config, it should
help minimize the delay between an IP address change and Ruddr detecting the
change.

**Sample config (with defaults commented)**::

    [notifier.main]
    type = systemd
    iface = eth0
    #ipv6_prefix = 64
    #interval = 1800
    #retry_min_interval = 10
    #retry_max_interval = 600
    #allow_private = no

**Configuration options:**

Note that the configuration options are exactly the same as the iface notifier,
since it uses the same exact polling behavior between notifications from
systemd-networkd.

``iface``
   The network interface whose address should be checked.

``ipv6_prefix``
   Number of bits that make up the network prefix of the IPv6 address. This is
   the part of the IPv6 address Ruddr will monitor for changes, and the part
   that will be updated by any attached updaters. The bits after the prefix are
   ignored. The default is 64, but note that many ISPs will delegate a larger
   block of addresses (often an entire 56-bit prefix). You should check what
   prefix size your ISP delegates. Note that this only applies to IPv6
   addresses; Ruddr always monitors and updates entire IPv4 addresses.

``interval``
   The number of seconds between IP address checks under normal conditions.

``retry_min_interval``
   If an IP address check fails (i.e. IPv4 address is not available when
   ``ipv4_required`` is true or IPv6 address is not available when
   ``ipv6_required`` is true), the notifier goes into retry mode with
   exponential backoff. The first retry will occur ``retry_min_interval``
   seconds later. The interval will double for each subsequent retry until
   a retry fully succeeds or ``retry_max_interval`` is reached.

``retry_max_interval``
   When the retry interval reaches this duration in seconds, it remains
   constant until a retry succeeds. See ``retry_min_interval`` for more
   explanation.

``allow_private``
   The notifier always ignores link-local (sometimes called APIPA) IPv4 and
   IPv6 addresses (169.254.0.0/16, fe80::/10). By default, it also ignores
   private network addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
   fd00::/8), but if this option is true/on/yes/1, it does not.

Web Notifier
------------

Type: ``web``

A web notifier periodically queries a public webpage or API to obtain the
current public IP address. This is a great option for hosts behind a router
with network address translation (NAT).

Currently, web notifiers are quite primitive: they assume the entire response
is the IP address. There are public APIs that work well under that limitation
(e.g. `icanhazip.com <https://icanhazip.com/>`_, run by Cloudflare), however
there are also plans to enhance its functionality (see `issue #9`_).

.. _issue #9: https://github.com/dominickpastore/ruddr/issues/9

**Sample config (with defaults commented)**::

    [notifier.main]
    type = web
    url = https://icanhazip.com/
    #url6 = <default same as url>
    #timeout = 10
    #timeout6 = <default same as timeout>
    #ipv6_prefix = 64
    #interval = 10800
    #retry_min_interval = 60
    #retry_max_interval = 86400
    #allow_private = no

**Configuration options:**

``url``
   The URL to request IP addresses from. Normally, both IPv4 and IPv6 addresses
   will be requested from the same URL (by issuing separate requests over IPv4
   and IPv6). If a different URL should be used for IPv4 and IPv6, specify the
   IPv6 URL with ``url6``. Note that this option is mandatory, so if only IPv6
   is needed, you should specify the URL here but add ``skip_ipv4 = true`` to
   the configuration.

``url6``
   The URL to request IPv6 addresses from, if different from the URL to request
   IPv4 addresses. Note that this option cannot be used without ``url``. If
   only IPv6 is needed, you should use regular ``url`` but add
   ``skip_ipv4 = true`` to the configuration.

``timeout``
   The number of seconds to wait for a response from the HTTP server. If the
   server does not respond within this many seconds, Ruddr will abort the
   attempt and go into retry mode.

``timeout6``
   The number of seconds to wait for a response from the HTTP server when
   requesting the IPv6 address, if different from the timeout when requesting
   the IPv4 address. If the server does not respond within this many seconds,
   Ruddr will abort the attempt and go into retry mode.

``ipv6_prefix``
   Number of bits that make up the network prefix of the IPv6 address. This is
   the part of the IPv6 address Ruddr will monitor for changes, and the part
   that will be updated by any attached updaters. The bits after the prefix are
   ignored. The default is 64, but note that many ISPs will delegate a larger
   block of addresses (often an entire 56-bit prefix). You should check what
   prefix size your ISP delegates. Note that this only applies to IPv6
   addresses; Ruddr always monitors and updates entire IPv4 addresses.

``interval``
   The number of seconds between IP address checks under normal conditions.

``retry_min_interval``
   If an IP address check fails (i.e. IPv4 address is not available when
   ``ipv4_required`` is true or IPv6 address is not available when
   ``ipv6_required`` is true), the notifier goes into retry mode with
   exponential backoff. The first retry will occur ``retry_min_interval``
   seconds later. The interval will double for each subsequent retry until
   a retry fully succeeds or ``retry_max_interval`` is reached.

``retry_max_interval``
   When the retry interval reaches this duration in seconds, it remains
   constant until a retry succeeds. See ``retry_min_interval`` for more
   explanation.

Static Notifier
---------------

Type: ``static``

This is a basic notifier that always returns the address specified in its
configuration. It is of limited use other than for testing purposes.

**Sample config (with defaults commented)**::

    [notifier.main]
    type = static
    ipv4 = 198.51.100.1
    ipv6 = 2001:db8:0001::/48

**Configuration options:**

Note that you must provide at least one of ``ipv4`` and ``ipv6``.

``ipv4``
   The IPv4 address that this notifier will always notify with.

``ipv6``
   The IPv6 network prefix that this notifier will always notify with. Note
   that the prefix length is required, and all non-prefix bits of the address
   must be zero.
