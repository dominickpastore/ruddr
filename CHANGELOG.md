Ruddr Changelog
===============

Ruddr uses [Semantic Versioning][semver]. In summary, new major versions
contain breaking changes, new minor versions contain new features, and new
patch versions contain bugfixes. (There is one minor deviation: Pre-release
versions will use [PEP 440][pep440] formatting, e.g.  "1.0.0b1", not the
hyphenated "1.0.0-beta.1" form specified by Semantic Versioning.)

[Unreleased]
------------

This is the initial release of Ruddr. It includes:

- Support for Linux and instructions for setup with systemd
- Notifiers:
  * IFace notifier
  * Basic web notifier (more flexible web notifier coming in a later release)
  * Systemd notifier
  * Static notifier for testing and diagnostic purposes
- Updaters:
  * Standard updater
  * Duck DNS updater
  * FreeDNS (afraid.org) updater
  * Gandi updater
  * Hurricane Electric Tunnel Broker updater
- Support for IPv6
- Support for extending Ruddr with your own updaters and notifiers
- Persistent storage for the last successful update, to avoid sending duplicate
  updates
- Support for running Ruddr as a library

[semver]: https://semver.org/
[pep440]: https://www.python.org/dev/peps/pep-0440/#version-scheme

[Unreleased]: https://github.com/dominickpastore/ruddr
