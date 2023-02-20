Help Resources
==============

.. contents:: Contents
   :local:
   :depth: 1
   :backlinks: none

Frequently Asked Questions
--------------------------

.. contents::
   :local:
   :backlinks: none

Why another dynamic DNS client?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This project started as a way to scratch a personal itch: Existing dynamic DNS
clients didn't support IPv6 in a very useful way (if at all).

Existing clients checked the public address of the current host and kept that
address updated at your dynamic DNS provider. For IPv4, where network address
translation is the norm, that worked well. That one address would be shared by
the entire network. For IPv6, that same strategy *could* work, but since ISPs
typically delegate an entire IPv6 prefix to your network, each host generally
had its own globally-routable IPv6 address. With existing clients, if there
were more than one host, that meant each one had to run its own DDNS client.

Ruddr works like most clients did for IPv4, but takes a different strategy for
IPv6: It monitors only the network prefix portion of the address. When it
detects a change, it updates the address for multiple hosts by replacing only
their prefixes, preserving the existing host portions. That way, it can update
addresses for the entire network, while still using only monitoring the current
address on a single host.

What if I don't want IPv6?
~~~~~~~~~~~~~~~~~~~~~~~~~~

If hosts in your network don't receive IPv6 addresses (other than link-local
addresses, which Ruddr ignores), Ruddr will usually do the right thing by
default: If no IPv6 addresses are found, it won't publish any. However, being
explicit will ensure Ruddr doesn't waste resources looking for an IPv6 address
when it doesn't need to (and ensures there are no surprises if a host does
happen to obtain an IPv6 address somehow).

There are two ways to explicitly disable publishing IPv6 addresses:

1. Set ``skip_ipv6 = true`` in the config sections for each of your notifiers.

2. Use the ``notifier4`` configuration option instead of ``notifier``. (See
   :ref:`updater_config`).

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

How do I get Ruddr to fetch the latest Public Suffix List?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ruddr can use the `Public Suffix List`_ in some of its updaters to infer which
zone each domain belongs to. It fetches a copy of the list when it first runs
and caches it indefinitely. Most users will never need Ruddr to fetch a new
copy, especially if they are not adding new domains to be updated. But, if for
some reason you do, you can force Ruddr to fetch a new copy by deleting the
cached copy.

The cached copy resides in Ruddr's configured ``datadir`` (``/var/lib/ruddr``
by default). Delete the entire ``tldextract`` directory inside. Next time Ruddr
needs the Public Suffix List, it will download a new copy.

.. _Public Suffix List: https://publicsuffix.org/

I just set up Ruddr on a new host but it's not publishing the address! Why not?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some updaters (particularly those that work with a DNS provider's general API,
rather than a dedicated dynamic DNS service) will only publish new addresses
when there's already an existing DNS record for the host. If your provider has
a web-based control panel, try putting in A and/or AAAA records for all the
hosts that need to be kept updated.

If the records-to-be-updated already exist, the issue will need further
investigation. Try posting a question in the discussions_ tab on GitHub.

I disabled IPv6. Why is Ruddr leaving my IPv6 address set?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ruddr does not unpublish any address without a new one to publish in its place.
(If it does unpublish an address, that is a bug, and you should `report it
<submit an issue>`_.) There are two reasons for that:

- Ruddr avoids touching any addresses it's not configured to touch, in order to
  avoid unexpectedly breaking non-dynamic addresses. This includes not touching
  IPv6 addresses for a host when it's configured to only update IPv4, and vice
  versa.

- If Ruddr *is* configured to handle IPv6 but the notifier can't currently
  obtain an IPv6 address, Ruddr assumes it may be a transient issue (e.g. a
  link is down). In that case, the last address may still be valid, and Ruddr
  does not want to risk unsetting a potentially valid address.

How can I tell if something went wrong?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ruddr does its best to do some useful work even when there are problems. For
example, if an updater is configured to update two domain names, and one has a
typo, Ruddr will generally still update the other. This does have the effect
that a small problem may not be obvious, since Ruddr will keep chugging along.

The best way to tell if there's a problem is to monitor the logs (which go to
the syslog by default). Ruddr will log a message at the warning level if there
is a potential problem and at the error or critical level if there is a
definite problem.

.. _issues:

Issues and Bugs
---------------

If you have found an issue with Ruddr, feel free to `submit an issue`_ on
GitHub. All issues and bug reports are welcome, but there are a few things you
can do to help things move more smoothly:

- Mention which versions of Python and Ruddr you have installed. If you are not
  sure, you can check with::

      python3 --version
      pip show ruddr

- Describe the incorrect behavior you are observing and the behavior you
  expected.

- If there are any error messages or stack traces, include those in the report.

- Paste a copy of the configuration you are using.

- Attach log messages leading up to the problem.

- Include any other information you think might be relevant.

Of course, not all of the above will apply to all types of issues. And just to
reiterate, *all* issues and bug reports are welcome, even if they are light on
details.

.. _feature requests:

Feature Requests
----------------

If there is a feature missing from Ruddr that you would like to see added, or
a DDNS provider that you would like to see support for, feel free to `submit an
issue`_ on GitHub. Alternatively, you can post on the discussions_ tab if you
prefer.

Suggestions for improving this documentation are also very welcome. You can
`submit an issue`_ or post on the discussions_ tab for that as well.

Additional Help
---------------

The goal is to make this documentation as thorough as possible, but if you find
you need a bit of human help, feel free to post in the discussions_ tab on
GitHub. I do my best to keep an eye on those and respond.

Currently, there is no mailing list, IRC channel, or discord server. The
project is not yet big enough to warrant them.

.. _discussions: https://github.com/dominickpastore/ruddr/discussions
.. _submit an issue: https://github.com/dominickpastore/ruddr/issues
.. _submit a pull request: https://github.com/dominickpastore/ruddr/pull
