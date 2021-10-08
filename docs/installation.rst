Installation
============

Basic Installation
------------------

Ruddr is available on PyPI under the name |ruddr|_. Install it with pip like
this::

    pip3 install ruddr

.. |ruddr| replace:: ``ruddr``
.. _ruddr: https://pypi.org/project/ruddr/

At this point, the ``ruddr`` command line script will be available, but it
still needs to be configured. Proceed to :doc:`usage`. In addition, if you
would like to use the ``systemd`` notifier, there are some extra steps,
described below.

Systemd Notifier
----------------

.. note::
   The steps below are only required for the ``systemd`` notifier, which ties
   into systemd-networkd to trigger updates as soon as the network status
   changes. They are NOT required if you just want to run Ruddr as a systemd
   service.

The ``systemd`` notifier depends on PyGObject, which cannot be trivially
installed from PyPI. The recommended way to install it is by following the
instructions on `PyGObject's Getting Started page`_.  If you are not installing
Ruddr in a virtual environment, you should be set after that.

If you *are* using a virtual environment, you may discover that PyGObject does
not like to be installed inside it. The easiest way to get this working is to
allow system site packages when creating your virtual environment::

    python3 -m venv --system-site-packages <venv-directory>

Then, you can follow the usual instuctions from `PyGObject's Getting Started
page`_, and your virtual environment will access the systemwide PyGObject
package.

Finally, if you want to try and install PyGObject from PyPI despite the warning
above, you can do so with the ``systemd`` optional extra, which adds PyGObject
as a dependency::

    pip3 install ruddr[systemd]

.. _PyGObject's Getting Started page: https://pygobject.readthedocs.io/en/latest/getting_started.html
