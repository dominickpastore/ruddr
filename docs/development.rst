For Developers
==============

If you are a developer, you may be interested in extending Ruddr with your own
notifier and/or updater modules. Or, you may want to integrate Ruddr's
functionality into a larger program. Or, you may just be looking for info about
contributing to the project. In any case, this page is for you.

.. contents::
   :backlinks: none

.. module:: ruddr

.. TODO Note exceptions under each section they affect

.. _notifier_dev:

Writing Your Own Notifier
-------------------------

.. TODO

.. _updater_dev:

Writing Your Own Updater
------------------------

An updater in Ruddr is, at its core, a class that provides two methods: one to
update the IPv4 address and one to update the IPv6 address(es). That being
said, there's more to implementing those methods than it may seem at first
glance, so Ruddr provides a few base classes that lay the groundwork for
several common types of APIs. Each of these provides certain abstract methods
appropriate to the specific style of API they support.

**To create an updater:** Create a class that inherits from one of these base
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

.. _high level updaters:

High-Level Updater Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: OneWayUpdater
   :members:

.. autoclass:: TwoWayUpdater
   :members:

.. autoclass:: TwoWayZoneUpdater
   :members:

.. _low level updaters:

Low-Level Updater Classes
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: Updater
   :members: publish_ipv4, publish_ipv6, replace_ipv6_prefix

.. autoclass:: BaseUpdater
   :members:

Using your Custom Updater
~~~~~~~~~~~~~~~~~~~~~~~~~

Once you have a custom updater class, there are two ways to start using it.

**The first way** is by module name and class name. For this to work, the
module containing your updater class must be in the module search path.
Typically, this means you'll either have to install it or make sure the
``PYTHONPATH`` environment variable includes the path to your module when Ruddr
is run. Then, if your updater is class ``MyUpdater`` in a file named
``myupdater.py``, you can use an updater configuration like this::

    [updater.main]
    module = myupdater
    type = MyUpdater
    # ...

**The second way** to start using it is by creating a Python package with a
``ruddr.updater`` entry point. This requires slightly more work upfront (you
have to create a ``pyproject.toml``), but has the advantage that it becomes
very easy to publish your updater to PyPI for others to use, if you so choose.
If you want to go this route, you can follow these steps:

1. Set up an empty directory for your package and put the module containing
   your updater inside. In the simplest case, the module may be a single
   ``.py`` file, but it can be a package with submodules, etc. For simplicity,
   we will assume the module is a single Python file, ``myupdater.py``, and
   the updater class inside is ``MyUpdater``.

2. If you intend to share your updater, e.g. on PyPI, GitHub, or otherwise, you
   may want to create a ``README.md`` in the same directory.

3. Create a file ``pyproject.toml`` in the directory with contents similar to
   this::

       [build-system]
       requires = ["setuptools>=61.0"]
       build-backend = "setuptools.build_meta"

       [project]
       # This becomes the package name on PyPI, if you choose to publish it
       name = "ruddr_updater_myupdater"
       version = "0.0.1"
       authors = [
           { name="Your Name", email="your_email@example.com" },
       ]
       description = "My Ruddr Updater"
       # Uncomment the next line if you created a README
       #readme = "README.md"
       requires-python = ">=3.7"
       classifiers = [
           "Programming Language :: Python :: 3",
       ]

       [project.entry-points."ruddr.updater"]
       my_updater = "myupdater:MyUpdater"

   Be sure to set the name, version, authors, and description as appropriate,
   but that last section is the important part. In that example, an entry point
   named ``my_updater`` is created in the ``ruddr.updater`` group, and it
   points to the ``MyUpdater`` class in the ``myupdater`` package.

4. You now have an installable Python package. Use ``pip install -U .`` to
   install it from the current directory. (If you wish to make it public, you
   can also publish it to PyPI and install it by name.)

5. The entry point name, ``my_updater`` in the example above, can be used as
   the updater ``type`` in your Ruddr config, for example::

       [updater.main]
       type = my_updater
       # ...

Using Ruddr as a Library
------------------------

Ruddr's primary use case is as a standalone service, but it can be integrated
into other Python programs as a library as well. The steps boil down to this:

1. First, create an instance of :class:`~ruddr.Config`. It can be created
   directly, or you may use :func:`~ruddr.read_file` or
   :func:`~ruddr.read_file_from_path`.

2. Use the :class:`~ruddr.Config` to create a :class:`~ruddr.DDNSManager`

3. TODO

.. TODO

The APIs for these classes and functions are below.

.. autofunction:: read_file

.. autofunction:: read_file_from_path

.. autoclass:: Config
   :members:

.. TODO DDNSManager needs a better docstring

.. autoclass:: DDNSManager
   :members:

Ruddr Exceptions
----------------

.. TODO

Development on Ruddr Itself
---------------------------

.. TODO

Installation for Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. TODO Installing from repository

Running Tests
~~~~~~~~~~~~~

.. TODO Currently only tests are for style. Install with .[test]

.. TODO Run full test suite with tox. HTML coverage report generated.
   Can also run individual tools: "flake8", "python setup.py check -m -s",
   "pytest", "pytest --cov", "pytest --cov-report=html"

Generating Docs
~~~~~~~~~~~~~~~

.. TODO Install with .[docs]

Contributions
-------------

.. TODO note that issues and feature requests are also helpful, send to
   appropriate section on help page

Contributing Updaters and Notifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. TODO How to add to repo, run tests, add docs ideally, then open pull request
.. TODO If do not want to merge code into Ruddr, can also upload to PyPI with
        entry points. Will be supported soon.

Other Code Contributions
~~~~~~~~~~~~~~~~~~~~~~~~

.. TODO
