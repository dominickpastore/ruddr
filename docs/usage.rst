Configuration and Usage
=======================

.. note::
   If you have not already done so, you should read :doc:`howitworks` before
   continuing.

Configuration File
------------------

.. TODO necessary for any run

Usage
-----

.. TODO command line flags, single shot updates

Running as a Service
--------------------

Generally speaking, any system that can start a Python script at boot and
ideally send a SIGTERM at shutdown can run Ruddr as a service. Instructions for
setting this up with systemd, one of the most widely used init systems on Linux
servers, are below. Hopefully, instructions for other systems will come soon.

.. TODO info on contributing instructions and examples

Systemd
~~~~~~~

.. TODO setting up a systemd service
