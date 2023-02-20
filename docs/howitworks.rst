How Ruddr Works
===============

If you have never used Ruddr before, this page describes the basic design. Some
concepts will be familiar if you have used other dynamic DNS clients before,
but others will be new.

The diagram below represents an example Ruddr configuration:

.. graphviz::
    :alt: Example Config

    digraph "Example Config" {
        rankdir="LR";

        icanhazip [shape=plaintext,label="icanhazip.com"];
        eth0 [shape=plaintext];

        node [shape=box,color=crimson];
        notifier4 [label="Web notifier"]
        notifier6 [label="IFace notifier"]

        icanhazip -> notifier4;
        eth0 -> notifier6;

        node [shape=box,color=dodgerblue3];
        updater1 [label="Standard updater"]
        updater2 [label="FreeDNS updater"]

        edge [label="192.0.2.47"];
        notifier4 -> updater1;
        edge [label="\n192.0.2.47"];
        notifier4 -> updater2;
        edge [label="2001:db8:47::/64"];
        notifier6 -> updater2;

        edge [label=""];
        node [shape=oval,style=dashed,color=black];
        updater1 -> "Dynu";
        updater2 -> "Afraid.org";
    }

On the left, we have sources for our current IP addresses. In this case,
suppose we want to use the IPv6 address assigned to ``eth0`` and fetch our IPv4
address from icanhazip.com. On the right, we have dynamic DNS providers. Let's
say we have A records at both Dynu and Afraid.org and AAAA records at
Afraid.org. Ruddr's job is to ensure the providers always have the current IP
addresses from the sources, and it does this through **notifiers** (in red) and
**updaters** (in blue).

Updaters
--------

An updater's job is to publish IP addresses to a dynamic DNS provider.
Typically, there will be one updater per provider. There are different types of
updaters depending on the protocol your dynamic DNS provider uses.

In the example above, there is one updater that publishes to Dynu using the de
facto standard /nic/update protocol and one updater that publishes to
Afraid.org using the FreeDNS protocol native to that site.

Notifiers
---------

The notifier's job is to obtain the current IP address that updaters will
publish. There are different ways to accomplish this, so there are different
notifiers available to suit the needs of each environment.

For example, if your router is assigned a public, globally-routable IP address
by your ISP, the iface notifier can just check the current IP address on your
WAN interface periodically.

However, if Ruddr is running on a host inside your LAN, behind NAT, you can use
the the web notifier. It can check the public IP address using a website like
`icanhazip.com <https://icanhazip.com>`_.

Tying Them Together
-------------------

Each updater is tied to one IPv4 notifier and one IPv6 notifier (or the same
notifier for both). The process of checking and publishing a new IP address
goes like this:

1. A notifier checks the current IP address and provides it to Ruddr.
2. For each updater configured to use this notifier:

   a. Ruddr sends the IP address to the updater for publishing.
   b. The updater checks the last IP address it published. If it matches, it
      skips steps (c) and (d).
   c. The updater sends the new IP address to the provider.
   d. The updater reports whether it was successful. If so, it stores the new
      IP address for the next time step (b) runs. If not, Ruddr schedules a
      retry for later. [#updatefail]_

Handling IPv6
-------------

IPv6 poses a new problem for dynamic DNS. Like with IPv4, most ISPs will not
provide fixed addresses, or at least not without payment or a special
agreement. However, unlike IPv4, IPv6 is not usually routed with NAT, meaning
there is not one single public address covering your entire network. Typically,
your ISP will assign you a prefix, and every device in your network will pick a
public, globally-routable address with that prefix.

Ruddr was designed to handle this situation. Notifiers only monitor the
prefix portion of IPv6 addresses, since that's the only part changed by the
ISP. Updaters assume there may be multiple addresses to update, and they
change only the prefix on each one. This way, even if you need to support IPv6,
you can still have centralized DDNS management.

.. rubric:: Footnotes

.. [#updatefail] There's technically more nuance to this: When an update fails,
   the updater "forgets" the last published IP address, since it has no way of
   knowing whether the old IP address is still published or not (e.g. the new
   IP could be published, but updater's connection broke and it never received
   the success response from the provider). That way, if the notifier sends a
   new IP address before a successful retry, it will *always* proceed to step
   (c). (Ruddr also cancels any pending retries whenever the notifier sends a
   new IP address, as those retries now contain a stale IP address.)
