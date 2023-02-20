For Developers
==============

If you are a developer, you may be interested in extending Ruddr with your own
notifier and/or updater modules. Or, you may want to integrate Ruddr's
functionality into a larger program. Or, you may just be looking for info about
contributing to the project. In any case, this page is for you.

.. note::
   If you have questions or comments on developing updaters, notifiers, or any
   other Ruddr development, feel free to start a `discussion on GitHub`_. I
   especially welcome feedback about this developer documentation.

   .. _discussion on GitHub: https://github.com/dominickpastore/ruddr/discussions

.. contents:: Contents
   :local:
   :backlinks: none

.. module:: ruddr
   :noindex:

.. _notifier_dev:

Writing Your Own Notifier
-------------------------

A notifier in Ruddr is a class that monitors a source of IP address information
and calls a notify function from time to time with the current address. The
goal, of course, is to tell Ruddr about a new IP address shortly after it
changes.

Most notifiers will fall into one of a few categories:

Event-based
   Monitor some external source of events providing new IP addresses.

.. TODO for example, the passthrough notifier will do this

Polling
   Poll the current IP address periodically through some means and notify each
   time. For example, this is what the ``iface`` and ``web`` notifiers do.

Event-triggered lookup
   Monitor some external source of events to know when the IP address changes,
   and then check what the current IP address is through some other means. For
   example, the ``systemd`` notifier does this: systemd-networkd sends a DBus
   event when there is a network status change, and when the notifier receives
   it, it checks the current address assigned to the network interface.

.. note::
   There is no harm in notifying extra times, i.e. when the address *hasn't*
   changed. In fact, polling-style notifiers rely on it. Ruddr keeps track of
   the address most recently sent to each provider and doesn't send duplicates.

Ruddr provides a convenient base class, :class:`Notifier`, which can be used
to implement all three styles of notifier. It boils down to a few core methods:

:meth:`~Notifier.setup`
   This abstract method is called when it's time to start the notifier. If the
   notifier needs to subscribe to any event sources, open any connections,
   start any background threads, etc., this is the place to do it.

:meth:`~Notifier.teardown`
   The opposite of :meth:`~Notifier.setup`: This abstract method is called when
   it's time to stop the notifier. It should clean up any connections,
   resources, threads, etc. that are no longer needed.

:meth:`~Notifier.check_once`
   For notifiers that support checking the current IP address(es) on demand,
   this abstract method should do so. It's called after
   :meth:`~Notifier.setup`, when Ruddr receives SIGUSR1, and can be set to run
   periodically with :meth:`~Notifier.set_check_intervals`.

:meth:`~Notifier.set_check_intervals`
   This provides a way to set :meth:`~Notifier.check_once` to run
   automatically on an interval. It also allows you to set the retry delay for
   when it fails (whether it's scheduled to run automatically or not). Call it
   in the constructor of your notifier, if necessary.

Any new notifier should begin by inheriting from :class:`Notifier`, and then
its constructor needs to be written. The constructor's main job here is to
1) call the superclass constructor and 2) read any required parameters from the
configuration. The constructor signature must match this:

.. function:: Notifier.__init__(name, config)
   :noindex:

   :param name: Notifier name, taken from ``[notifier.<name>]`` in the Ruddr
                config
   :type name: str
   :param config: A :class:`dict` of this notifier's configuration values, all
                  as strings, plus any global configuration options that may
                  be useful (currently, only ``datadir``, which notifiers may
                  use to cache data if necessary).
   :type config: Dict[str, str]

If there are any errors in the configuration, catch them in the constructor and
raise :exc:`ConfigError`. The constructor is also the place to call
:meth:`~Notifier.set_check_intervals`, if necessary (but more on that in the
following sections). Note that the constructor is *not* the place to do any
setup that should happen as part of notifier startup—that should happen in
:meth:`~Notifier.setup`.

After calling the superclass constructor, two member variables will be
available for your convenience: ``self.name``, containing the name of the
notifier, and ``self.log``, a Python logger named after the notifier. You are
encouraged to use ``self.log`` often.

The rest of the implementation varies depending on the style of notifier. The
next three sections, one for each style, discuss that in more detail. Following
those is an API reference for the :class:`Notifier` class.

.. _notifying ipv4 and ipv6:

.. note::
   **Handling IPv4 vs. IPv6 Addressing**

   Different networks will have different requirements for IPv4 vs. IPv6
   addressing: Some may require one or both, some may not, some may want to
   ignore one or both. Notifiers must handle this properly, and the
   :class:`Notifier` class has methods to help.

   - If your notifier has config that's required only for IPv4 or only for
     IPv6, be sure to implement the :meth:`~Notifier.ipv4_ready` and
     :meth:`~Notifier.ipv6_ready` functions.

   - Ruddr may not need both IPv4 and IPv6 addresses from your notifier. It
     should call :meth:`~Notifier.want_ipv4` and :meth:`~Notifier.want_ipv6`,
     and if either returns ``False``, there is no need to notify for that type
     of address at all.

   - Even if an address type is wanted, it may or may not be an error if your
     notifier can't obtain it. If :meth:`~Notifier.need_ipv4` returns ``True``
     but :meth:`~Notifier.check_once` cannot currently obtain an IPv4 address,
     your notifier should raise :exc:`NotifyError` (after notifying for the
     other address type, if necessary). The same goes for
     :meth:`~Notifier.need_ipv6` and IPv6 addressing. (This bullet point does
     not apply if :meth:`~Notifier.check_once` is not implemented.)

.. _event-based notifier:

Event-Based Notifiers
~~~~~~~~~~~~~~~~~~~~~

This style of notifier receives events from some external source with the
current IP address. Since it gets IP addresses from these events, it can't
check the IP address on-demand, so this style of notifier will leave
:meth:`~Notifier.check_once` unimplemented and doesn't need to call
:meth:`~Notifier.set_check_intervals`.

It should, however, implement :meth:`~Notifier.setup` and
:meth:`~Notifier.teardown`. Typically, :meth:`~Notifier.setup` would involve
setting up a thread to listen on a socket, or setting up a callback for some
event, or something along those lines. Then, :meth:`~Notifier.teardown` would
do the opposite.

Be sure to follow the guidelines in the :ref:`note about IPv4 and IPv6
addressing <notifying ipv4 and ipv6>` above. Then, whenever an IPv4 address or
IPv6 prefix is received, call :meth:`~Notifier.notify_ipv4` or
:meth:`~Notifier.notify_ipv6`.

Be careful not to leave your notifier in an invalid state if
:meth:`~Notifier.teardown` happens at an inconvenient time. It's guaranteed not
to be called before :meth:`~Notifier.setup` completes, but apart from that, it
is up to you to ensure that anything happening in a background thread isn't
interrupted in a way that breaks it.

.. TODO for an example, look at the sources for PassthroughNotifier.

.. _polling notifiers:

Polling Notifiers
~~~~~~~~~~~~~~~~~

This style of notifier is fairly simple. It periodically checks the current IP
address and notifies each time.

Start by calling :meth:`~Notifier.set_check_intervals` in the constructor. That
will usually look something like this (but customize the values according to
your needs)::

    self.set_check_intervals(retry_min_interval=60,
                             retry_max_interval=86400,
                             success_interval=10800,
                             config=config)

The first three parameters set default values, and the last one provides the
config dict, which will override those defaults with any entries that match
(see the API documentation for :meth:`~Notifier.set_check_interval`).

The important part there is that ``success_interval`` is set to a default other
than zero. That causes the notifier to automatically call
:meth:`~Notifier.check_once` periodically, waiting that many seconds between
calls (assuming there were no errors).

The ``retry_min_interval`` and ``retry_max_interval`` parameters control what
happens if there is an error in :meth:`~Notifier.check_once` (more
specifically, if it raises :exc:`NotifyError`). Such an error triggers the
retry logic, which uses an exponential backoff. The first retry is after
``retry_min_interval`` seconds. If it fails again, each successive retry
interval is twice as long, maxing out at ``retry_max_interval``. Once the retry
interval reaches the max, it remains constant until the call succeeds. As soon
as a retry succeeds, the notifier returns to calling
:meth:`~Notifier.check_once` every ``success_interval`` seconds.

With :meth:`~Notifier.set_check_intervals` out of the way, it's time to
implement :meth:`~Notifier.check_once`. That's where the core functionality of
a polling notifier happens. Taking care to follow the guidelines in the
:ref:`note about IPv4 and IPv6 addressing <notifying ipv4 and ipv6>` above,
implement the logic to fetch the current IP address(es) and call
:meth:`~Notifier.notify_ipv4` and/or :meth:`~Notifier.notify_ipv6`.

For many polling notifiers, that will be the entire implementation. Since
setting ``success_interval`` causes the checks to happen automatically, there's
not usually a need to implement :meth:`~Notifier.setup` or
:meth:`~Notifier.teardown`. Nonetheless, they can be implemented if necessary.

For an example of this style of notifier, look at the sources for
:class:`ruddr.notifiers.web.WebNotifier` or
:class:`ruddr.notifiers.iface.IFaceNotifier`.

Event-Triggered Lookup Notifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This style of notifier is sort of a hybrid between the other two. It receives
events when the current IP address may have changed, but still has to look up
the IP address itself to find out what it is.

The strategy here is to implement the IP address lookup functionality in
:meth:`~Notifier.check_once` as with :ref:`polling notifiers`, but set
``success_interval`` to zero. That way, the retry logic is still there, and
on-demand notifying when Ruddr receives SIGUSR1 will work, but otherwise,
:meth:`~Notifier.check_once` will only run when the notifier triggers it by
calling :meth:`~Notifier.check`.

If you already read through the instructions for :ref:`polling notifiers`, the
first part here is going to look pretty familiar.

Start by calling :meth:`~Notifier.set_check_intervals` in the constructor. That
will generally look something like this::

    self.set_check_intervals(retry_min_interval=60,
                             retry_max_interval=86400,
                             success_interval=0,
                             config=config)

The important part there is that ``success_interval`` is set to zero. That's
what stops the notifier from automatically calling :meth:`~Notifier.check_once`
except in the retry logic. (That being said, there is no reason a notifier
can't have automatic polling *and* trigger extra checks itself, if that would
be useful. In fact, that's what the ``systemd`` notifier does.)

The ``retry_min_interval`` and ``retry_max_interval`` parameters control what
happens if there is an error in :meth:`~Notifier.check_once` (more
specifically, if it raises :exc:`NotifyError`). Such an error triggers the
retry logic, which uses an exponential backoff. The first retry is after
``retry_min_interval`` seconds. If it fails again, each successive retry
interval is twice as long, maxing out at ``retry_max_interval``. Once the retry
interval reaches the max, it remains constant until the call succeeds.

The retry parameters directly passed in to the function act as defaults. If the
config dict contains keys matching the names ``retry_min_interval`` or
``retry_max_interval``, those take precedence.

Next, implement :meth:`~Notifier.check_once`. As mentioned, this is where the
logic to look up the current IP address should go. It should call
:meth:`~Notifier.notify_ipv4` and/or :meth:`~Notifier.notify_ipv6` with the
addresses it obtains. Make sure to follow the guidelines in the :ref:`note
about IPv4 and IPv6 addressing <notifying ipv4 and ipv6>`.

That takes care of the IP address lookup part. Next is the events for changed
IP addresses. For that part, you will need to implement :meth:`~Notifier.setup`
and :meth:`~Notifier.teardown`. As with the :ref:`event-based notifier` style
above, :meth:`~Notifier.setup` would typically involve setting up a thread to
listen on a socket, setting up a callback for some event, or something along
those lines, and :meth:`~Notifier.teardown` would do the opposite.

Finally, whenever your notifier becomes aware that the IP address may have
changed, call :meth:`~Notifier.check`. That will call
:meth:`~Notifier.check_once`, but will properly handle the retries for you.

For an example of this style of notifier, look at the sources for
:class:`ruddr.notifiers.systemd.SystemdNotifier`. (One caveat: That notifier
also uses polling, but setting ``success_interval=0`` in the call to
:meth:`~Notifier.set_check_intervals` would disable that.)

Notifier Base Class
~~~~~~~~~~~~~~~~~~~

.. autoclass:: Notifier
   :members: set_check_intervals, notify_ipv4, notify_ipv6, want_ipv4,
             want_ipv6, need_ipv4, need_ipv6, ipv4_ready, ipv6_ready, setup,
             teardown, check_once

.. _updater_dev:

Writing Your Own Updater
------------------------

An updater in Ruddr is, at its core, a class that provides two methods: one to
update the IPv4 address and one to update the IPv6 address(es). That being
said, those methods are actually responsible for quite a bit, such as detecting
duplicate notifies, working with the addrfile, and retrying failed updates.
Ruddr provides a few base classes that handle all those responsibilities and
lay the groundwork for several common types of dynamic DNS provider APIs. Each
of them provides certain abstract methods appropriate to the specific style of
API they support.

To create an updater, create a class that inherits from one of those base
classes, listed below, and implement its abstract methods as described under
:ref:`high level updaters`.

:class:`OneWayUpdater`
    A base class for providers with "one way" protocols. That is, protocols
    that allow domain updates but have no way to check the current address(es)
    assigned to domains. It obtains the current address using DNS lookups
    instead.

:class:`TwoWayUpdater`
    A base class for providers with "two way" protocols. That is, protocols
    that allow updating the address(es) at a domain name *as well as* querying
    the current address at a domain name. It's best suited for providers whose
    API has no concept of zones (e.g. there's no API calls related to zones,
    nor does any operation require a zone as a parameter).

:class:`TwoWayZoneUpdater`
    This is like :class:`TwoWayUpdater`, except it's well-suited for providers
    whose APIs *do* care about zones. For example, this is the base class to
    use if there is a way to query all records for a zone, or if domain updates
    require specifying the zone for the update.

Those three base classes should cover the vast majority of use cases. However,
if you need even more flexibility, you can inherit directly from the low-level
:class:`Updater` base class instead, or the most primitive, the
:class:`BaseUpdater` base class. These are described under :ref:`low level
updaters`.

A few additional guidelines and tips:

- All updaters must have a constructor that matches the following:

  .. function:: Updater.__init__(name, addrfile, config)
     :noindex:

     :param name: Updater name, taken from ``[updater.<name>]`` in the Ruddr
                  config
     :type name: str
     :param addrfile: The :class:`~ruddr.Addrfile` object this updater should use
     :type addrfile: ruddr.Addrfile
     :param config: A :class:`dict` of this updater's configuration values, all
                    as strings, plus any global configuration options that may
                    be useful (currently, only ``datadir``, which updaters may
                    use to cache data if necessary).
     :type config: Dict[str, str]

- The first two parameters (``name`` and ``addrfile``) can be passed directly
  to the super class constructor, and it's strongly recommended that that be
  the first thing your constructor does (so the variables in the next bullet
  point will be initialized).

- The :class:`BaseUpdater` class, which is a superclass of all updaters
  (directly or indirectly), makes the ``self.name`` and ``self.log`` member
  variables available. ``self.name`` is a :class:`str` with the updater name
  and ``self.log`` is a Python logger named after the updater. You may use
  either of these variables whenever convenient, but you are especially
  encouraged to use ``self.log`` often.

.. _high level updaters:

High-Level Updater Base Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: OneWayUpdater
   :members:

.. autoclass:: TwoWayUpdater
   :members:

.. autoclass:: TwoWayZoneUpdater
   :members:

.. _low level updaters:

Low-Level Updater Base Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: Updater
   :members: publish_ipv4, publish_ipv6, replace_ipv6_prefix

.. autoclass:: BaseUpdater
   :members:

.. _using custom:

Using your Custom Updater or Notifier
-------------------------------------

Once you have a custom updater or notifier class, there are two ways to start
using it.

**The first way** is by module name and class name. For this to work, the
module containing your updater/notifier class must be in the module search
path. Typically, this means you'll either have to install it or make sure the
``PYTHONPATH`` environment variable includes the path to your module when Ruddr
is run. Then, you can use the ``module`` and ``type`` options in your updater
or notifier config, and Ruddr will import and use it.

For example, suppose you have an updater class ``MyUpdater`` in a file named
``myupdater.py``. Assuming that Python file is in some directory in your
``PYTHONPATH``, you can use an updater configuration like this::

    [updater.main]
    module = myupdater
    type = MyUpdater
    # ...

.. _second way:

**The second way** to start using it is by creating a Python package with a
``ruddr.updater`` or ``ruddr.notifier`` entry point. This requires slightly
more work upfront (you have to create a ``pyproject.toml``), but has the
advantage that it becomes very easy to publish your updater or notifier to PyPI
for others to use, if you so choose. If you want to go this route, you can
follow these steps:

1. Set up an empty directory for your package and put the module containing
   your updater or notifier inside. In the simplest case, the module may be a
   single ``.py`` file, but it can be a package with submodules, etc. For
   demonstration, we will assume you have a notifier in a single-file Python
   module, ``mynotifier.py``, and the notifier class inside is ``MyNotifier``.

2. If you intend to share your updater or notifier, e.g. on PyPI, GitHub, or
   otherwise, you may want to create a ``README.md`` in the same directory.

3. Create a file ``pyproject.toml`` in the directory with contents similar to
   this::

       [build-system]
       requires = ["setuptools>=61.0"]
       build-backend = "setuptools.build_meta"

       [project]
       # This becomes the package name on PyPI, if you choose to publish it
       name = "ruddr_notifier_mynotifier"
       version = "0.0.1"
       authors = [
           { name="Your Name", email="your_email@example.com" },
       ]
       description = "My Ruddr Notifier"
       # Uncomment the next line if you created a README
       #readme = "README.md"
       requires-python = ">=3.7"
       classifiers = [
           "Programming Language :: Python :: 3",
       ]

       [project.entry-points."ruddr.notifier"]
       my_notifier = "mynotifier:MyNotifier"

   Be sure to set the name, version, authors, and description as appropriate,
   but that last section is the important part. In that example, an entry point
   named ``my_notifier`` is created in the ``ruddr.notifier`` group, and it
   points to the ``MyNotifier`` class in the ``mynotifier`` module.

4. You now have an installable Python package. Use ``pip install -U .`` to
   install it from the current directory. (If you wish to make it public, you
   can also publish it to PyPI and install it by name.)

5. Once installed, the entry point name, ``my_notifier`` in the example above,
   can be used as the notifier ``type`` in your Ruddr config. For example::

       [notifier.main]
       type = my_notifier
       # ...

Using Ruddr as a Library
------------------------

Ruddr's primary use case is as a standalone service, but it can be integrated
into other Python programs as a library as well. The steps boil down to this:

1. First, create an instance of :class:`Config`. It can be created directly, or
   you may use :func:`read_config` or :func:`read_config_from_path`.

2. Use the :class:`Config` to create a :class:`DDNSManager`.

3. Call :func:`~DDNSManager.start` on the :class:`DDNSManager` you created.
   This will return once Ruddr finishes starting. Ruddr runs in background
   non-daemon threads ("non-daemon" meaning that your program will not end
   until they are stopped as described in the next step).

4. When ready for Ruddr to stop, call :func:`~DDNSManager.stop` on your
   :class`DDNSManager` object. Ruddr will halt the background threads
   gracefully.

An immediate update (if possible) can be triggered on a started
:class:`DDNSManager` by calling its :func:`~DDNSManager.do_notify` method.
This is not always possible if the configured notifiers do not support it,
though most do.

See the next section for the APIs involved.

.. warning::
   The config file reader functions can throw :exc:`ConfigError`. The
   :class:`DDNSManager` constructor can raise :exc:`ConfigError` and its
   :func:`~DDNSManager.start` function can raise :exc:`NotifierSetupError`. Be
   ready to handle those exceptions. Both of them can be caught under
   :exc:`RuddrSetupError`.

Manager and Config API
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: read_config

.. autofunction:: read_config_from_path

.. autoclass:: Config
   :members:

.. autoclass:: DDNSManager
   :members:

.. _exceptions:

Ruddr Exceptions
----------------

Below is a summary of all the exceptions that can be raised by Ruddr or in
custom notifiers and updaters. Note that the rest of the API documentation on
this page describes more precisely when particular exceptions might be raised
and when it's appropriate for subclasses to raise them.

.. autoexception:: RuddrException
   :show-inheritance:

.. autoexception:: RuddrSetupError
   :show-inheritance:

.. autoexception:: ConfigError
   :show-inheritance:

.. autoexception:: NotifierSetupError
   :show-inheritance:

.. autoexception:: NotStartedError
   :show-inheritance:

.. autoexception:: NotifyError
   :show-inheritance:

.. autoexception:: PublishError
   :show-inheritance:

.. autoexception:: FatalPublishError
   :show-inheritance:

Development on Ruddr Itself
---------------------------

Everything discussed so far on this page has been about development that ties
into Ruddr. This section is for development *on Ruddr itself*, for example
fixing bugs or adding new features.

Installation for Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The latest sources for Ruddr are available on GitHub_. Once you have cloned the
repo, the easiest way to work on development is to optionally set up a virtual
environment, then install directly out of the repo with the ``dev`` extra.

Assuming you have a shell open in the repo::

    # Optionally, set up a virtual environment
    python3 -m venv venv
    . venv/bin/activate
    # Install in develop mode with the "dev" extra
    pip install -U -e .[dev]

The ``dev`` extra includes everything required to check style, check types,
run unit tests, and regenerate the documentation.

.. _testing:

Running Tests
~~~~~~~~~~~~~

Ruddr's full set of checks and tests can be run with tox. It includes style
checks and linting, type checking, and unit tests with coverage. If you
installed with the ``dev`` extra above, you have everything you need.
(Alternatively, the ``test`` extra includes just the testing tools from the
``dev`` extra.)

To run the full test suite, make sure your virtual environment is active (if
you are using one) and run the ``tox`` command::

   # Skip this line if not using a virtual environment
   . venv/bin/activate
   tox

This will first run ``flake8`` and ``pytype``. Then it will run ``pytest`` with
coverage on each supported version of Python. Lastly, it will generate the
coverage report in the terminal and write it to htmlcov/index.html.

These tools can also be run individually:

- ``flake8 src/ test/``
- ``pytype``
- ``pytest --cov``

Generating Docs
~~~~~~~~~~~~~~~

The documentation is available online at https://ruddr.dcpx.org/, but if you
would like to generate a local copy (for reference or to preview changes),
install the ``docs`` extra (the ``dev`` extra includes the ``docs`` extra) and
build the docs in ``docs/`` as usual for Sphinx::

    # Assuming you are in the git repo:
    pip install .[docs]
    cd docs
    make html

Open ``docs/_build/html/index.html`` to read them.

You can also generate other formats with ``make <format>``, provided the
necessary tools are available (e.g. ``make latexpdf`` requires a LaTeX
distribution to be installed). The output will be in ``docs/_build/<format>/``.

Contributions
-------------

If you have code you would like to contribute, please feel free to `submit a
pull request on GitHub <pull request>`_. (Note that :ref:`issues` and
:ref:`feature requests` are also helpful and very much appreciated!)

There are a few guidelines that make it more likely a PR can be accepted:

- Generally speaking, development happens on the ``dev`` branch. The ``master``
  branch is reserved for released code only. (If you submit a pull request to
  ``master``, we will change it to ``dev``.)

- The automated test suite should run when pull requests are submitted. If
  there are any problems, you should do your best to fix them (or explain why
  the test is flagging when it shouldn't). Code that passes has a much higher
  chance of being accepted than code that fails. See :ref:`testing` above.

- Pay attention to code style. Flake8 runs as part of the test suite. ``#noqa``
  is allowed, but with good reason.

- If you add new functionality, it has a higher chance of being accepted if you
  add additional documentation and tests to go with it. The automated test
  suite generates a code coverage report, both locally and online at TODO.

- Pull requests need not be related to an existing issue, but if you submit one
  that is, you should reference the issue number somewhere in the pull request.

None of these are automatic deal breakers if you do not follow them, but
following them does increase the chances of your pull request being accepted.

All merged code contributions will be mentioned in the `CHANGELOG`_ with
attribution to the contributor.

.. TODO add link to code coverage report

Contributing Updaters and Notifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have written a new updater or notifier and wish to share it with the
community, you have two options:

1. Contribute it for inclusion in Ruddr itself. To do this:

   a. Add a new .py file with your updater/notifier under the appropriate
      package in the Ruddr sources (``src/ruddr/updaters`` or
      ``src/ruddr/notifiers``)
   b. Add a new entry to the :data:`~ruddr.updaters.updaters` or
      :data:`~ruddr.notifiers.notifiers` dict in the ``__init__.py`` file in
      the same directory. The key will become the built-in type name of the
      updater or notifier, used for the ``type=`` config option. The value
      must be the class for the new updater/notifier.
   c. Add documentation for the new updater/notifier. Add a new section to
      ``docs/updaters.rst`` or ``docs/notifiers.rst`` listing the name, a brief
      description of the updater/notifier, a sample config snippet, and a
      detailed list of the configuration options it accepts.
   d. Open a `pull request`_.

2. If you would prefer to independently maintain your updater or notifier, you
   can publish it to PyPI with a ``ruddr.updater`` or ``ruddr.notifier`` entry
   point. Anyone who installs your updater/notifier from PyPI will then be able
   to use that entry point name as a ``type=`` option in their config.

   For example, if you declare this entry point in your ``pyproject.toml``::

       [project.entry-points."ruddr.updater"]
       my_updater = "myupdater:MyUpdater"

   then someone can use your ``myupdater.MyUpdater`` class as an updater with
   this Ruddr config snippet::

       [updater.foo]
       type = my_updater
       # ... other config for the updater

   For more information on publishing an updater like this, see the
   :ref:`second method <second way>` under :ref:`using custom`.

Some conventions when developing updaters or notifiers for inclusion in Ruddr:

- Make liberal use of the logger, especially when there is a problem. In
  particular, Ruddr uses exceptions mainly to control contingency behavior
  when there is a problem. The exception message is, for the most part,
  ignored. That's not to say exceptions shouldn't carry an appropriate message,
  but the primary way errors are communicated to the user is through logging.
  If there is a problem, an error should always be logged (critical if the
  problem is fatal to the updater/notifier), and a warning should be logged for
  potential problems.
- Do as much useful work as possible, even if errors require skipping some
  parts. For example, if an updater can't update one domain due to a typo in
  its name, it should still update the rest of the configured domains.
- Don't trust any input, whether from user config or API calls. For example, an
  improperly formatted IP address should be caught, logged, and an appropriate
  :ref:`Ruddr exception <exceptions>` raised, preventing a :exc:`ValueError`
  from crashing the whole program.

.. _GitHub: https://github.com/dominickpastore/ruddr
.. _pull request: https://github.com/dominickpastore/ruddr/pulls
.. _CHANGELOG: https://github.com/dominickpastore/ruddr/blob/master/CHANGELOG.md
