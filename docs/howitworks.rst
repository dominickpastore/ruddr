How Ruddr Works
===============

If you have never used Ruddr before, this page describes the basic design. Some
concepts will be familiar if you have used other dynamic DNS clients before,
but others will be new.

The diagram below represents an example Ruddr configuration:

.. TODO change edge labels to actual IP addresses, since it looks like the
   notifiers communicate with updaters using IPv4 and IPv6, which is not the
   case.

.. graphviz::
    :alt: Example Config

    digraph "Example Config" {
        rankdir="LR";

        icanhazip [shape=plaintext,label="icanhazip.com"];
        eth0 [shape=plaintext];

        node [shape=box,color=crimson];
        notifier4 [label="Web notifier"]
        notifier6 [label="Timed notifier"]

        icanhazip -> notifier4;
        eth0 -> notifier6;

        node [shape=box,color=dodgerblue3];
        updater1 [label="Standard updater"]
        updater2 [label="FreeDNS updater"]

        edge [label="IPv4"];
        notifier4 -> updater1;
        notifier4 -> updater2;
        edge [label="IPv6"];
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
by your ISP, the timed notifier can just check the current IP address on your
WAN interface periodically.

However, if Ruddr is running on a host inside your LAN, behind NAT, you can use
the the web notifier. It can check the public IP address using a website like
icanhazip.com.

Tying Them Together
-------------------

Each updater is tied to one IPv4 notifier and one IPv6 notifier (or the same
notifier for both). The process of checking and publishing a new IP address
goes like this:

1. A notifier checks the current IP address and provides it to Ruddr.
2. For each updater configured to use this notifier:

   a. Ruddr checks the last IP address published by this updater. If it
      matches, it skips steps (b) and (c).
   b. Ruddr sends the IP address to the updater for publishing.
   c. The updater reports whether it successfully published the IP address. If
      so, Ruddr stores the new IP address for the next time step (a) runs. If
      not, Ruddr schedules a retry for later. [#updatefail]_

.. rubric:: Footnotes

.. [#updatefail] There's technically more nuance to this: When an update fails,
   Ruddr "forgets" the last published IP address, since it has no way of
   knowing whether the old IP address is still published or not (e.g. the new
   IP could be published, but updater's connection broke and it never received
   the success response from the provider). That way, if the notifier sends a
   new IP address before a successful retry, it will *always* proceed to step
   (b). (Ruddr also cancels any pending retries whenever the notifier sends a
   new IP address, as those retries now contain a stale IP address.)
