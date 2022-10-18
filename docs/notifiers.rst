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

Timed Notifier
--------------

Type: ``timed``

A timed notifier periodically checks the IP address of an attached network
interface. This is a good choice when Ruddr is running on your router itself.

**Sample config (with defaults commented)**::

    [notifier.main]
    type = timed
    iface = eth0
    #ipv6_prefix = 64
    #interval = 1800
    #retry_min_interval = 10
    #retry_max_interval = 600
    #allow_private = no
    #skip_ipv4 = no
    #skip_ipv6 = no
    #ipv4_required = yes
    #ipv6_required = no

**Configuration options:**

``iface``
   The network interface whose address should be checked.

``ipv6_prefix``
   Number of bits that make up the network prefix of the IPv6 address. This is
   the part of the IPv6 address Ruddr will monitor for changes, and the part
   that will be updated by any attached updaters. The bits after the prefix
   will not be monitored, nor will they be changed by any attached notifier.
   The default is 64, but note that many ISPs will delegate a larger block of
   addresses (often an entire 56-bit prefix). You should check what prefix size
   your ISP delegates. Note that this only applies to IPv6 addresses; Ruddr
   always monitors and updates entire IPv4 addresses.

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
   Ruddr always ignores link-local (sometimes called APIPA) IPv4 and IPv6
   addresses (169.254.0.0/16, fe80::/10). By default, it also ignores private
   network addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fd00::/8),
   but if this option is true/on/yes/1, it does not.

Systemd Notifier
----------------

Type: ``systemd``

A systemd notifier is *very* similar to a timed notifier, with just one
additional feature: It ties in to systemd-networkd via DBus to detect when
interfaces go up or down immediately. On systems where systemd-networkd manages
the network config, this should help minimize the delay between an IP address
change and Ruddr detecting the change.

**Sample config (with defaults commented)**::

    [notifier.main]
    type = systemd
    iface = eth0
    #ipv6_prefix = 64
    #interval = 1800
    #retry_min_interval = 10
    #retry_max_interval = 600
    #allow_private = no
    #skip_ipv4 = no
    #skip_ipv6 = no
    #ipv4_required = yes
    #ipv6_required = no

**Configuration options:**

Note that the configuration options are exactly the same as the timed notifier,
since it shares the same exact polling behavior when systemd-networkd does not
notify of changed IP addresses.

``iface``
   The network interface whose address should be checked.

``ipv6_prefix``
   Number of bits that make up the network prefix of the IPv6 address. This is
   the part of the IPv6 address Ruddr will monitor for changes, and the part
   that will be updated by any attached updaters. The bits after the prefix
   will not be monitored, nor will they be changed by any attached notifier.
   The default is 64, but note that many ISPs will delegate a larger block of
   addresses (often an entire 56-bit prefix). You should check what prefix size
   your ISP delegates. Note that this only applies to IPv6 addresses; Ruddr
   always monitors and updates entire IPv4 addresses.

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
   Ruddr always ignores link-local (sometimes called APIPA) IPv4 and IPv6
   addresses (169.254.0.0/16, fe80::/10). By default, it also ignores private
   network addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fd00::/8),
   but if this option is true/on/yes/1, it does not.

Web Notifier
------------

Type: ``web``

A web notifier periodically queries a public webpage or API to obtain the
current public IP address. This is a great option for hosts behind a router
doing network address translation (NAT).

Currently, web notifiers are quite primitive: they assume the entire response
is the IP address. There are public APIs that work well under that limitation
(e.g. `icanhazip.com <https://icanhazip.com/>`_, run by Cloudflare), however
there are also plans to enhance its functionality (see `issue #9`_).

.. _issue #9: https://github.com/dominickpastore/ruddr/issues/9

.. TODO

Static Notifier
---------------

Type: ``static``

.. TODO
