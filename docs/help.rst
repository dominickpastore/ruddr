Help Resources
==============

.. TODO discussions page

Frequently Asked Questions
--------------------------

.. TODO

Why another dynamic DNS client?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. TODO Existing clients don't support IPv6 well, if at all. Also scratching a
   bit of a personal itch, with the need to support a DNS provider whose API
   wasn't part of existing popular clients.

What if I don't want IPv6?
~~~~~~~~~~~~~~~~~~~~~~~~~~

If hosts in your network don't receive IPv6 addresses (other than link-local
addresses, which Ruddr always ignores), there is no need to do anything
special. Ruddr won't publish IPv6 addresses if it doesn't find any.

.. TODO Does it *unpublish* IPv6 addresses if there was one and it's no longer
   there? What about if IPv6 updating is deconfigured?

However, if you would like to explicitly disable publishing IPv6 addresses,
there are two ways:

1. Set ``skip_ipv6 = true`` in the config sections for each of your notifiers.

2. Use the ``notifier4`` configuration option instead of ``notifier``. (See
   :ref:`updater_config`).

.. TODO Does this unset a previously published IPv6 address?

What if I want IPv6, but I want behavior like IPv4 (i.e. no prefix logic)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For IPv6, Ruddr normally makes the assumption that only the prefix portion of
the address will change. Usually, this is the correct behavior, as hosts would
be configured to use a static interface identifier (the last 64 bits of their
address). However, if that is not the case in your network, you can work around
this by configuring the network prefix to be 128 bits in your notifiers.

The drawback to doing this is if you need to set up dynamic DNS for multiple
hosts in the network, they will likely each need to run their own instance of
Ruddr (since a centralized instance of Ruddr won't have easy access to the
full addresses of each host when they change).

Issues and Bugs
---------------

.. TODO How to report

Feature Requests
----------------

.. TODO How to request
