"""Python implementation of sd_notify(3)

The official python-systemd package on PyPI to notify systemd of daemon status
has not had a release since 2017 (it's near the end of 2021), despite having
several fixes since then, including a memory leak fix for notify().

There are a few alternatives:

1. Write a C extension module or use ctypes or CFFI or similar to tie in to
   the C call, sd_notify(3). This probably means using pkg-config, either in
   the build stage or at runtime, and not breaking when systemd isn't there.
   Lots of moving parts for a small feature. Bleh.
2. Use :func:`os.system` to call ``systemd-notify``.
3. Turns out the notify protocol is fairly straightforward, and just involves
   writing a simple string to a Unix socket provided in an environment
   variable. We can do that easily in pure Python.

So this module does option 3.
"""

import socket
import os

def _notify(msg):
    """Send the given bytes to the systemd notify socket named in the
    environment. If not on a Unix-like system or no notify socket was named,
    do nothing.

    :param msg: The :class:`bytes` to send
    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    # Check if running on Unix
    try:
        af = socket.AF_UNIX
    except AttributeError:
        return

    # Check if running systemd
    if not os.path.isdir('/run/systemd/system/'):
        return

    # Get the socket name, if set
    try:
        sock_name = os.environ['NOTIFY_SOCKET']
    except KeyError:
        return
    #sock_name = os.fsencode(sock_name)
    if sock_name[0] == 0x40:    # 0x40 is @
        #sock_name = b'\x00' + sock_name[1:]
        sock_name = '\x00' + sock_name[1:]

    sock_type = socket.SOCK_DGRAM
    try:
        sock_type |= socket.SOCK_CLOEXEC
    except AttributeError:
        pass
    with socket.socket(af, sock_type) as sock:
        sock.sendmsg([msg], [], 0, sock_name)

def _args_to_bytes(**kwargs):
    """Convert keyword args to a :class:`bytes` object ready to send to the
    notify socket

    :param kwargs: The arguments to be converted. Generally, argument names
                   should be all caps, like READY or STATUS. See
                   ``sd_notify(3)`` for more info on what they mean.
    :raises UnicodeEncodeError: if any of the arguments cannot be encoded as
                                UTF-8
    """
    msg = bytearray()
    for arg, val in kwargs.items():
        arg_bytes = arg.encode('utf-8')
        val_bytes = str(val).encode('utf-8')
        msg += arg_bytes + b'=' + val_bytes + b'\n'
    return bytes(msg)

def ready():
    """Send a READY notification to systemd, if on a platform with systemd and
    a notify socket was provided. Otherwise, do nothing.

    This tells systemd that the service is fully running.

    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(READY=1))

def reloading():
    """Send a RELOADING notification to systemd, if on a platform with systemd
    and a notify socket was provided. Otherwise, do nothing.

    This tells systemd that the service is reloading its configuration. The
    caller must send a READY notification when finished reloading config.

    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(RELOADING=1))

def stopping():
    """Send a STOPPING notification to systemd, if on a platform with systemd
    and a notify socket was provided. Otherwise, do nothing.

    This tells systemd that the service is shutting down.

    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(STOPPING=1))

def status(msg):
    """Send a STATUS notification to systemd, if on a platform with systemd
    and a notify socket was provided. Otherwise, do nothing.

    This is used to provide a freeform status message to systemd.

    :param msg: The status message to send.
    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    :raises UnicodeEncodeError: if the given message cannot be encoded as UTF-8
    """
    _notify(_args_to_bytes(STATUS=msg))

def errno(err):
    """Send an ERRNO notification to systemd, if on a platform with systemd
    and a notify socket was provided. Otherwise, do nothing.

    This tells systemd that the service has failed, and gives an errno code as
    the cause.

    :param err: The error number (as stored in ``errno``). Should be an
                :class:`int`.
    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(ERRNO=err))

def buserror(err):
    """Send a BUSERROR notification to systemd, if on a platform with systemd
    and a notify socket was provided. Otherwise, do nothing.

    This tells systemd that the service has failed, and gives a DBus-style
    error code as the cause (e.g. "org.freedesktop.DBus.Error.TimedOut").

    :param err: The error code. Should be a string.
    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    :raises UnicodeEncodeError: if the given error code cannot be encoded as
                                UTF-8
    """
    _notify(_args_to_bytes(BUSERROR=err))

def watchdog():
    """Send a WATCHDOG=1 notification to systemd, if on a platform with systemd
    and a notify socket was provided. Otherwise, do nothing.

    This sends the watchdog keep-alive message, required periodically if
    ``WatchdogSec`` is set for the service.

    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(WATCHDOG=1))

def watchdog_trigger():
    """Send a WATCHDOG=trigger notification to systemd, if on a platform with
    systemd and a notify socket was provided. Otherwise, do nothing.

    This tells systemd to immediately trigger a watchdog expiration and take
    the appropriate actions.

    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(WATCHDOG='trigger'))

def watchdog_usec(usec):
    """Send a WATCHDOG_USEC notification to systemd, if on a platform with
    systemd and a notify socket was provided. Otherwise, do nothing.

    This tells systemd to reset the WATCHDOC_USEC value to the one specified.
    See ``sd_notify(3)`` for more information.

    :param usec: The value to set WATCHDOC_USEC to. Should be an :class:`int`.
    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(WATCHDOG_USEC=usec))

def extend_timeout_usec(usec):
    """Send an EXTEND_TIMEOUT_USEC notification to systemd, if on a platform
    with systemd and a notify socket was provided. Otherwise, do nothing.

    This tells systemd to extend the startup, runtime, or shutdown timeout
    (whichever is currently relevant) to the given number of microseconds from
    the current time.

    :param usec: The value to extend the timeout with. Should be an
                 :class:`int`.
    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    """
    _notify(_args_to_bytes(EXTEND_TIMEOUT_USEC=usec))

def notify(**kwargs):
    """Send a notification to systemd with the given variables set. For most
    notifications, there is a function corresponding to that specific
    notification. However, there are a handful of notifications where that is
    not the case, and this function can be used to send them. It can also be
    used to send notifications with arbitrary variables set.

    If on a platform without systemd or if no notify socket was provided, do
    nothing.

    :param kwargs: Specifies the variables that should be set in the
                   notification. Argument names become the variable names, and
                   should, generally speaking, be in all caps. Argument values
                   become the variable values and should be either :class:`str`
                   or :class:`int` values.
    :raises OSError: if any errors occur, other than 1) because this is not a
                     system with systemd or 2) no notify socket was provided
                     (neither of which is considered an error)
    :raises UnicodeEncodeError: if an argument value cannot be encoded in UTF-8
    """
    _notify(_args_to_bytes(**kwargs))
