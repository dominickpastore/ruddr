#  Ruddr - Robotic Updater for Dynamic DNS Records
#  Copyright (C) 2023 Dominick C. Pastore
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import logging
import logging.handlers
import signal
import sys

from . import configuration, manager
from .exceptions import ConfigError, RuddrSetupError
from .util import sdnotify


def parse_args(argv):
    """Parse command line arguments

    :param argv: Either ``None`` or a list of arguments
    :returns: a :class:`argparse.Namespace` containing the parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Robotic Updater for Dynamic DNS Records",
        epilog="SIGUSR1 will cause a running instance to immediately check and"
               " update the current IP address(es) if possible",
    )
    parser.add_argument("-c", "--configfile", default="/etc/ruddr.conf",
                        help="Path to the config file")
    parser.add_argument("-d", "--debug-logs", action="store_true",
                        help="Increase verbosity of logging significantly")
    parser.add_argument("-s", "--stderr", action="store_true",
                        help="Log to stderr instead of syslog or file")
    return parser.parse_args(argv)


def main(argv=None):
    """Main entry point when run as a standalone program

    :param argv: List of arguments. If ``None``, read :data:`sys.argv`.
    """
    args = parse_args(argv)
    try:
        conf = configuration.read_config_from_path(args.configfile)
    except ConfigError as e:
        print("Config error:", e, file=sys.stderr)
        sys.exit(2)

    if args.stderr:
        conf.logfile = 'stderr'

    if conf.logfile == 'syslog':
        log_handler = logging.handlers.SysLogHandler()
    elif conf.logfile == 'stderr':
        log_handler = logging.StreamHandler()
    else:
        log_handler = logging.FileHandler(conf.logfile)
    log = logging.getLogger('ruddr')
    log.addHandler(log_handler)

    if args.debug_logs:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    # Start up the actual DDNS code
    try:
        ddns_manager = manager.DDNSManager(conf)
        ddns_manager.start()
    except RuddrSetupError:
        log.critical("Ruddr failed to start.")
        sys.exit(1)

    # Notify systemd, if applicable
    sdnotify.ready()

    # Do an immediate update on SIGUSR1
    def handle_sigusr1(sig, _):
        log.info("Received signal: %s", signal.Signals(sig).name)
        ddns_manager.do_notify()
    signal.signal(signal.SIGUSR1, handle_sigusr1)

    # Wait for SIGINT (^C) or SIGTERM
    def handle_signals(sig, _):
        log.info("Received signal: %s", signal.Signals(sig).name)
        sdnotify.stopping()
        ddns_manager.stop()
    signal.signal(signal.SIGINT, handle_signals)
    signal.signal(signal.SIGTERM, handle_signals)
