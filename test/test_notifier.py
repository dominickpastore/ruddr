import ruddr

# TODO test ipv4_ready and ipv6_ready both raise errors when false

# TODO test ipv4_ready and ipv6_ready do not raise errors when false but not
#  attached to updater

# TODO test ipv4_ready and ipv6_ready do not raise errors when false but skipped

# TODO test that notifier that's only attached to a skipped family is not
#  started (it should also raise a critical error, but that need not be tested)

# TODO test that ipv4 and ipv6 both set to skip causes error to be raised

# TODO timed notifier retries after failed notify, then not again after
#  successful

# TODO timed notifier does not retry after failed notify and then immediate
#  manual successful notify

# TODO timed notifier repeats notify with success interval
