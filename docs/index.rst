Ruddr Documentation
===================

Welcome to the full documentation for Ruddr, the Robotic Updater for Dynamic
DNS Records.

Ruddr is a **modular** dynamic DNS client. It separates the job into two tasks:

- Detecting IP address changes, handled by *notifiers*.
- Publishing the changed addresses, handled by *updaters*

.. TODO link to updaters and notifiers page

Ruddr provides built-in updaters and notifiers for common use cases and
services. For example, the ``web`` notifier will periodically query a
what-is-my-ip style website, and the ``standard`` updater uses the de facto
standard API, ``http(s)://.../nic/update``, to publish updates for popular
services like DynDNS and NoIP.

.. TODO link to page about writing your own updaters and notifiers
.. TODO link to page about contributing notifiers

However, if the built-in updaters or notifiers do not meet your needs, Ruddr is
**extensible**. You can easily write your own and seamlessly tie it into your
configuration. (If you think your custom notifier will be useful to others,
feel free to submit a contribution!)

Finally, Ruddr does its best to make dynamic DNS work with **IPv6**, despite
the fact that hosts are not likely behind network address translation (NAT).

Quick Links
-----------

.. TODO PyPI

- `This documentation <https://ruddr.dcpx.org/>`_
- `GitHub, README <https://github.com/dominickpastore/ruddr>`_
- `Changelog
  <https://github.com/dominickpastore/ruddr/blob/master/CHANGELOG.md>`_

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   installation
   howitworks
   usage
   notifiers
   updaters
   development
   help

Index
-----

* :ref:`genindex`
* :ref:`search`

License
-------

Copyright © 2021 Dominick C. Pastore
