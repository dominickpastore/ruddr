Ruddr
=====

**Robotic Updater for Dynamic DNS Records**

Steer DNS queries to the proper IP addresses. *With support for IPv6!*

- PyPI: [https://pypi.org/project/ruddr/][PyPI]
- Documentation: [https://ruddr.dcpx.org/][docs]
- GitHub: [https://github.com/dominickpastore/ruddr][GitHub]
- Changelog:
  [https://github.com/dominickpastore/ruddr/blob/master/CHANGELOG.md][changelog]
- Issues: [https://github.com/dominickpastore/ruddr/issues][issues]
- Discussion: [https://github.com/dominickpastore/ruddr/discussion][discussion]

Overview
--------

Ruddr is a **modular** dynamic DNS client. It separates the job into two tasks:

- Detecting IP address changes, handled by *notifiers*.
- Publishing the changed addresses, handled by *updaters*

Ruddr provides built-in updaters and notifiers for common use cases and
services. For example, the `web` notifier will periodically query a
what-is-my-ip style website, and the `standard` updater uses the de facto
standard API, `http(s)://.../nic/update`, to publish updates compatible with
several well-known services. There are a variety of others; see the [full
documentation][docs] for the full list.

However, if the built-in notifiers or updaters do not meet your needs, Ruddr is
**extensible**. You can easily  write your own and tie it into your
configuration. (If you think your custom notifier will be useful to others,
feel free to submit a contribution, or you can upload it to PyPI yourself as an
extension!)

Finally (and the main reason Ruddr was born), Ruddr does its best to make
dynamic DNS work with **IPv6**, despite the fact that hosts are not likely
behind network address translation (NAT).

For more information about the built-in updaters and notifiers or writing your
own, see the [full documentation][docs].

Installation from PyPI
----------------------

At this time, Ruddr runs on Linux and possibly other Unix-like platforms.
Non-Unix-like platforms may be supported in the future.

It is available on PyPI under the name [`ruddr`][PyPI]. Basic installation
works similarly to any other Python package:

    pip3 install ruddr

Ruddr is now installed. You can continue to configuration.

**Note:** If you would like to use the `systemd` notifier, there are extra
steps. See the installation instructions in the [full documentation][docs] for
details.

Quick Start Guide
-----------------

1. Write this configuration to `/etc/ruddr.conf`:

       [ruddr]
       notifier = main

       [notifier.main]
       type = web
       url = https://icanhazip.com/

       [updater.main]
       # Updater config here

2. Paste in one of the updater configurations from the "Updaters" page in the
   [full documentation][docs]

3. Set up Ruddr to run as a service. If using systemd, create a new unit file
   at `/etc/systemd/system/ruddr.service`:

       [Unit]
       Description=Robotic Updater for Dynamic DNS Records
       After=network.target

       [Service]
       Type=notify
       ExecStart=ruddr
       NotifyAccess=main

       [Install]
       WantedBy=multi-user.target

   then enable and start the service (as root or with `sudo`):

       systemctl enable ruddr
       systemctl start ruddr

   If not using systemd, then using whatever means your system supports, set
   the `ruddr` script to run at startup, with SIGTERM sent to it at shutdown.

Full Documentation
------------------

The full documentation can be found here: [https://ruddr.dcpx.org/][docs]

It contains much more information, including the following:

- How Ruddr works
- Detailed usage and configuration instructions
- Descriptions and configuration info for all the built-in updaters and
  notifiers
- Information for developers, including how to write custom updaters and
  notifiers
- Frequently asked questions and additional help resources.

License
-------

TODO add license notice to files

Copyright &copy; 2023 Dominick C. Pastore

[docs]: https://ruddr.dcpx.org/
[GitHub]: https://github.com/dominickpastore/ruddr
[PyPI]: https://pypi.org/project/ruddr/
[changelog]: https://github.com/dominickpastore/ruddr/blob/master/CHANGELOG.md
[issues]: https://github.com/dominickpastore/ruddr/issues
[discussion]: https://github.com/dominickpastore/ruddr/discussion
