Configuration and Usage
=======================

.. note::
   If you have not already done so, you should read :doc:`howitworks` before
   continuing.

Ruddr must be configured before it can be used. After that, it's meant to be
run as a service (i.e. a daemon, in Unix terminology).

Quick Start Guide
-----------------

If you want to get going in as little time as possible, start here.

1. Write this configuration to ``/etc/ruddr.conf``::

     [ruddr]
     notifier = main

     [notifier.main]
     type = web
     url = https://icanhazip.com/

     [updater.main]
     # Updater config here

2. Paste in one of the updater configurations from the :doc:`updaters` page

3. Set up Ruddr as a service using the instructions appropriate for your system
   under :ref:`service`.

You now have a basic Ruddr configuration working. Keep reading if you would
like to learn more about Ruddr's features and how to tailor it to your needs.

Configuration
-------------

Ruddr expects to find its configuration at ``/etc/ruddr.conf`` by default, but
this can be changed with the ``-c``/``--configfile`` command line option (see
:ref:`usage`).

Here is a sample config::

  [ruddr]
  ## This directory is where Ruddr keeps runtime data, including:
  ## - The addrfile, used to keep track of the current address at each DDNS
  ##   provider
  ## - The tldextract cache, where a local copy of the Public Suffix List (PSL)
  ##   data is kept. This is used to infer zones for domain names if
  ##   necessary.
  ## The line below shows the default location. Uncomment it if you would like
  ## to change it.
  #datadir = /var/lib/ruddr

  ## Each updater must get its addresses from a particular notifier. You can
  ## optionally set a default notifier here, and it will be used whenever an
  ## updater doesn't specify its own notifier. (This is mainly useful if you
  ## have several DDNS providers that all need to be updated from the same
  ## source.)
  #notifier = icanhazip

  ## You can also set different default notifiers for IPv4 and IPv6.
  #notifier4 = icanhazip
  #notifier6 = wan_ip

  [notifier.icanhazip]
  ## Every notifier must specify a type, which determines how it obtains the
  ## current IP address. For example, the web notifier checks a "what is my IP"
  ## style website to get the current address. See the "Notifiers" section of
  ## the documentation for a list of built-in notifier types and their
  ## configuration options.
  ##
  ## Ruddr is extensible: If the notifier types that come with Ruddr do not
  ## suit your needs, it supports installing additional notifiers from PyPI.
  ## Or, you can even specify your own notifier class to import and the module
  ## to import it from, like this:
  ##
  ##   module = mynotifier
  ##   type = MyNotifierClass
  type = web

  ## Most notifiers will require extra config, like the URL for the web
  ## notifier. See the "notifiers" page in the documentation for details on
  ## the options available.
  url = https://icanhazip.com/

  [notifier.wan_ip]
  type = iface
  iface = eth0

  [updater.duck]
  ## Every updater must specify a type as well, which determines the protocol
  ## it uses to communicate with your DDNS provider. See the "Updaters" section
  ## of the documentation for a list of built-in updater types and their
  ## configuration options.
  ##
  ## As with notifiers, Ruddr allows you to install additional updaters from
  ## PyPI, or you can specify your own updater class by naming the module it
  ## should be imported from:
  ##
  ##  module = myupdater
  ##  type = MyUpdaterClass
  type = duckdns

  ## Each updater can specify its own notifier, like below. Otherwise, it will
  ## use the default notifier from the [ruddr] section.
  notifier = icanhazip
  ## You can also set different default notifiers for IPv4 and IPv6.
  #notifier4 = icanhazip
  #notifier6 = wan_ip

  ## Most updaters will require extra config, like a list of hosts or domain
  ## names to update. See the "updaters" page in the documentation for details
  ## on the options available.
  token = ...
  hosts = example1 example2

The basic format is similar to Microsoft INI files:

- Options are grouped into sections. Each section starts with a ``[heading]``
  in square brackets. There is a main section named ``[ruddr]`` and a section
  for each notifier and updater.

- Options are specified using a ``key=value`` or ``key: value`` syntax

- Spaces are optional around the equals sign or colon and will be trimmed

- Trailing spaces will be trimmed from the end of a line

- Leading spaces are trimmed, but keys in a section should all have the same
  level of indentation (otherwise they may be interpreted as multi-line values)

- Values can span multiple lines by indenting them more than the key (though
  this is rarely necessary).

- Lines starting with ``#`` or ``;`` are comments

The sections below describe how to customize each part of the configuration.

.. _notifier_config:

Notifiers
~~~~~~~~~

Notifiers monitor the current public IP address and "notify" when it has
changed. Most Ruddr configurations will need only a single notifier, or perhaps
a pair for IPv4 and IPv6.

A notifier configuration looks like this (with non-mandatory options
commented)::

  [notifier.<name>]
  #module = <module>
  type = <type>
  #skip_ipv4 = <true/false>
  #skip_ipv6 = <true/false>
  #ipv4_required = <true/false>
  #ipv6_required = <true/false>
  <additional config>

In the section heading, the notifier is given a unique name of your choice.

The ``module`` and ``type`` options let you specify the notifier type, which
determines how the current IP address is obtained. For example, the ``timed``
notifier periodically checks the IP address assigned to the current machine,
and the ``web`` notifier periodically checks a "what is my IP" style website.

- Ruddr comes with a variety of built-in notifier types, described on the
  :doc:`notifiers` page. The ``module`` option is not required when using
  these.

- Ruddr can be extended with notifiers from PyPI. Such notifiers will have
  their own type name for use with the ``type`` option. The ``module`` option
  is not required when using these. (If you are interested in publishing your
  own notifier on PyPI, see the :doc:`development` page.)

- You can develop your own notifier and have Ruddr import it. Specify the
  class name of the notifier with ``type`` and the module name it can be
  imported from with ``module``. See the :doc:`development` page for more info
  on how to develop a notifier.

The ``skip_ipv4``, ``skip_ipv6``, ``ipv4_required``, and ``ipv6_required``
options are used to control whether the notifier tries to fetch IPv4 and/or
IPv6 addresses and if it should consider it an error if it can't (which affects
how it retries).

.. note::
   The default settings try to fetch both IPv4 and IPv6 addresses, but consider
   it normal if only IPv4 works. That will work in a lot of situations, but if,
   for example, you know IPv6 addressing should or should not be working on
   your network, it's better to be explicit. It allows Ruddr to be more useful
   with retry behavior, among other things.

``skip_ipv4``
   If set to true/on/yes/1, this notifier will not try to fetch IPv4 addresses.
   (default false)

``skip_ipv6``
   If set to true/on/yes/1, this notifier will not try to fetch IPv6 addresses.
   (default false)

``ipv4_required``
   If set to true/on/yes/1, this notifier will treat failure to obtain an IPv4
   address as abnormal. If set to false/off/no/0, the notifier will not
   consider it a problem. For example, if an IPv4 address cannot be obtained
   when this is true, most notifier types will switch to a quick retry strategy
   with exponential backoff. If this is false, the notifier will proceed as if
   all is normal. (default true, ignored if ``skip_ipv4`` is true)

``ipv6_required``
   If set to true/on/yes/1, this notifier will treat failure to obtain an IPv6
   address as abnormal. If set to false/off/no/0, the notifier will not
   consider it a problem. For example, if an IPv6 address cannot be obtained
   when this is true, most notifier types will switch to a quick retry strategy
   with exponential backoff. If this is false, the notifier will proceed as if
   all is normal. (default false, ignored if ``skip_ipv6`` is true)

Most notifiers will require some extra configuration specific to that type of
notifier. For example, the ``timed`` notifier needs to know which network
interface to get the IP address from, and the ``web`` notifier needs to be
given the URL to query. See the :doc:`notifiers` page for lists of
configuration options for the built-in notifiers.

.. _updater_config:

Updaters
~~~~~~~~

Updaters are the interface between Ruddr and your dynamic DNS provider.
Most configurations will need only one, but if you have more than one provider,
you will need an updater for each one.

An updater configuration looks like this (with non-mandatory options
commented)::

  [updater.<name>]
  #module = <module>
  type = <type>
  #notifier = <notifier name>
  <additional config>

In the section heading, the updater is given a unique name of your choice.

As with notifiers, the ``module`` and ``type`` options let you specify the
updater type. There are different types for different protocols, so typically,
the type you choose will depend on your DDNS provider.

- Ruddr comes with a variety of built-in updater types. The built-in updaters
  cover a variety of popular DDNS services. See the :doc:`updaters` page for
  more information on which type to pick and configuration examples. The
  ``module`` option is not required when using a built-in updater type.

- Ruddr can be extended with updaters from PyPI. Such updaters will have their
  own type name for use with the ``type`` option. the ``module`` option is not
  required when using these. (If you are interested in publishing your own
  updater on PyPI, see the :doc:`development` page.)

- If neither of those choices suit your needs, you can develop your own updater
  and have Ruddr import it. Specify the class name of the updater with ``type``
  and the module name it can be imported from with ``module``. See the
  :doc:`development` page for more info on how to develop an updater.

Next, each updater must be associated with a notifier (or optionally, a pair of
notifiers, one for IPv4 and one for IPv6). Do this by setting the ``notifier``
option equal to the name of the notifier. If you want to set different
notifiers for the IPv4 and IPv6 address, use ``notifier4`` and ``notifier6``
instead.

Alternatively, if you leave out *all* ``notifier``, ``notifier4``, and
``notifier6`` options, Ruddr will use the default
``notifier``/``notifier4``/``notifier6`` options from the ``[ruddr]`` section.

.. note::
   If you *only* want to check and update IPv4 addresses, use *only*
   ``notifier4``. The same goes for IPv6 addresses only and ``notifier6``.
   Alternatively, you can specify ``skip_ipv4`` or ``skip_ipv6`` on the
   notifier and use regular ``notifier`` in the updater.

Most updaters will require some extra configuration specific to that type of
updater. For example, the ``standard`` updater needs a server address,
username, password, and a list of domain names to update. See the
:doc:`updaters` page for lists of configuration options for the built-in
updaters and sample configurations for popular DDNS providers.

Global Config
~~~~~~~~~~~~~

The optional ``[ruddr]`` section contains a few configuration options that
apply to Ruddr as a whole::

  [ruddr]
  datadir = /var/lib/ruddr
  notifier = <notifier name>
  log = <file path or syslog or stderr>

The ``datadir`` option specifies the path to a directory where Ruddr can keep
runtime data, including:

- The addrfile, where Ruddr keeps track of the IP address currently published
  with each provider
- The Public Suffix List cache, used to infer zones from fully-qualified domain
  names, if necessary (only used for certain types of updaters)

The default ``datadir`` is ``/var/lib/ruddr``.

The ``notifier`` option allows you to specify a default notifier. This is the
notifier that gets used for updaters that don't specify their own notifier. It
can be useful if you have multiple updaters that all need to get their IP
address from the same source. You can also use one or both of ``notifier4``
and ``notifier6`` in place of ``notifier``, as described under
:ref:`updater_config`. None of these ``notifier`` options are required if your
updaters all specify their own notifiers.

The ``log`` option allows you to specify where Ruddr should log to. The choices
are ``syslog`` (the default), ``stderr``, or a path to a logfile. (Note that
the ``-s``/``--stderr`` command line option overrides this.)

.. _usage:

Usage
-----

Normal usage of Ruddr involves configuring it to run as a service (see
:ref:`service`); however, it can be run at the command line for debugging.

After Ruddr is installed, the ``ruddr`` command is available to run it from the
command line. If you installed it in a virtual environment, that environment
will need to be activated first.

There are a few command line options:

``-h``/``--help``
   Display all the command line options and exit.

``-c``/``--configfile``
   Use the given config file instead of ``/etc/ruddr.conf``.

``-d``/``--debug-logs``
   Increase the verbosity of logging significantly.

``-s``/``--stderr``
   Log to stderr instead of the syslog or any configured logfile.

.. _service:

Running as a Service
--------------------

Once Ruddr is configured, it needs to be set up to run as a service. The
``ruddr`` script needs to be executed at startup and SIGTERM sent to it at
shutdown. Instructions for setting this up with systemd, one of the most widely
used init systems on Linux systems, are below.

We hope to add instructions for more systems in the future.

Systemd
~~~~~~~

Create a new systemd unit file at ``/etc/systemd/system/ruddr.service``::

  [Unit]
  Description=Robotic Updater for Dynamic DNS Records
  After=network.target

  [Service]
  Type=notify
  ExecStart=ruddr
  NotifyAccess=main

  [Install]
  WantedBy=multi-user.target

**Note if using a virtual environment:** You will need to replace the
``ExecStart`` line with something like this, where ``/path/to/venv/bin/python``
is the full absolute path to the ``python`` executable in your virtual
environment::

  ExecStart=/path/to/venv/bin/python -m ruddr

Then, simply enable and start the service (as root or with ``sudo``)::

  systemctl enable ruddr
  systemctl start ruddr
