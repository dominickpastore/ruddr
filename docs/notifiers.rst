Notifiers
=========

Notifiers monitor the current public IP address and "notify" when it has
changed. Since there are different ways to do this, there are a variety of
notifier types built into Ruddr. They are described below, along with their
configuration options and sample configurations.

If none of the built-in notifiers below meet your needs, Ruddr can be extended
with notifiers from PyPI, or you can write your own (see :ref:`notifier_dev`).

Timed Notifier
--------------

Type: ``timed``

A timed notifier periodically checks the IP address of an attached network
interface. This is a good choice when Ruddr is running on your router itself.

Sample config::

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

.. TODO

Systemd Notifier
----------------

Type: ``systemd``

.. TODO

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
