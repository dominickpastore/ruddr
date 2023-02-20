Ruddr Documentation
===================

Welcome to the full documentation for Ruddr, the Robotic Updater for Dynamic
DNS Records.

Ruddr is a **modular** dynamic DNS client. It separates the job into two tasks:

- Detecting IP address changes, handled by *notifiers*.
- Publishing the changed addresses, handled by *updaters*

Ruddr provides built-in updaters and notifiers for common use cases and
services. For example, the ``web`` notifier will periodically query a
what-is-my-ip style website, and the ``standard`` updater uses the de facto
standard API, ``http(s)://.../nic/update``, to publish updates for popular
services like DynDNS, Dynu, and NoIP. The :doc:`updaters` and :doc:`notifiers`
pages describe the rest of the built-in updaters and notifiers.

However, if the built-in updaters or notifiers do not meet your needs, Ruddr is
**extensible**. You can easily write your own and seamlessly tie it into your
configuration. (If you think your custom notifier will be useful to others,
feel free to submit a contribution, or you can upload it to PyPI yourself as
an extension!) See the :doc:`development` page for more information on that.

Finally (and the main reason Ruddr was born), Ruddr does its best to make
dynamic DNS work with **IPv6**, despite the fact that hosts are not likely
behind network address translation (NAT).

Quick Links
-----------

- `PyPI <https://https://pypi.org/project/ruddr/>`_
- `This documentation <https://ruddr.dcpx.org/>`_
- `GitHub, README <https://github.com/dominickpastore/ruddr>`_
- `Changelog
  <https://github.com/dominickpastore/ruddr/blob/master/CHANGELOG.md>`_
- `Issues <https://github.com/dominickpastore/ruddr/issues>`_
- `Discussion <https://github.com/dominickpastore/ruddr/discussion>`_

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

Copyright © 2023 Dominick C. Pastore
