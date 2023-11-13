Ruddr Changelog
===============

Ruddr uses [Semantic Versioning][semver]. In summary, new major versions
contain breaking changes, new minor versions contain new features, and new
patch versions contain bugfixes. (There is one minor deviation: Pre-release
versions will use [PEP 440][pep440] formatting, e.g.  "1.0.0b1", not the
hyphenated "1.0.0-beta.1" form specified by Semantic Versioning.)

[0.0.1b3] - 2023-11-12
----------------------

### Fixed

- Do not crash when systemd or iface notifier attempt to check the IP address
  of an interface that currently has no address

[0.0.1b2] - 2023-03-14
----------------------

### Fixed

- No longer crashes at startup without `-s` option

[0.0.1b1] - 2023-03-13
----------------------

This is the initial beta release of Ruddr. It includes:

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

[Unreleased]: https://github.com/dominickpastore/ruddr/compare/v0.0.1b3...dev
[0.0.1b3]: https://github.com/dominickpastore/ruddr/compare/v0.0.1b2...v0.0.1b3
[0.0.1b2]: https://github.com/dominickpastore/ruddr/compare/v0.0.1b1...v0.0.1b2
[0.0.1b1]: https://github.com/dominickpastore/ruddr/compare/v0.0.0...v0.0.1b1
