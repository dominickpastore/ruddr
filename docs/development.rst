For Developers
==============

If you are a developer, you may be interested in extending Ruddr with your own
notifier and/or updater modules. Or, you may want to integrate Ruddr's
functionality into a larger program. Or, you may just be looking for info about
contributing to the project. In any case, this page is for you.

.. module:: ruddr

.. TODO Note exceptions under each section they affect

.. _notifier_dev:

Writing Your Own Notifier
-------------------------

.. TODO

.. _updater_dev:

Writing Your Own Updater
------------------------

.. TODO

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

.. TODO exceptions

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
