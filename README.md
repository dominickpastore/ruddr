Ruddr
=====

**Robotic Updater for Dynamic DNS Records**

Steer DNS queries to the proper IP addresses. *With support for IPv6!*

- Documentation: [https://ruddr.dcpx.org/][docs]
- GitHub: [https://github.com/dominickpastore/ruddr][GitHub]
- Changelog:
  [https://github.com/dominickpastore/ruddr/blob/master/CHANGELOG.md][changelog]
- Issues: [https://github.com/dominickpastore/ruddr/issues][issues]

Overview
--------

Ruddr is a modular dynamic DNS client. It separates the job into two tasks:

- Detecting IP address changes, handled by *notifiers*.
- Publishing the changed addresses, handled by *updaters*

Ruddr provides built-in updaters and notifiers for common use cases and
services. For example, the `web` notifier will periodically query a
what-is-my-ip style website, and the `standard` updater uses the de facto
standard API, `http(s)://.../nic/update`, to publish updates for popular
services like DynDNS and NoIP.

If the built-in notifiers or updaters do not meet your needs, Ruddr makes it
easy to write your own and tie it into your configuration. (If you think your
custom notifier will be useful to others, feel free to submit a contribution!)
TODO link to contributions page for docs, with section on contributing
notifiers and updaters

For more information about the built-in updaters and notifiers or writing your
own, see the [full documentation][docs].

TODO More sections
------------------

License
-------

TODO add license notice to files

Copyright &copy; 2021 Dominick C. Pastore

[docs]: https://ruddr.dcpx.org/
[GitHub]: https://github.com/dominickpastore/ruddr
[changelog]: https://github.com/dominickpastore/ruddr/blob/master/CHANGELOG.md
[issues]: https://github.com/dominickpastore/ruddr/issues
