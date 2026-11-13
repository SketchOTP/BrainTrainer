# Local network habitat

Open http://<lan-ip>:46341/ on a phone connected to the same LAN.
The existing desktop URL http://127.0.0.1:<port>/ also remains available.
Both listeners serve the same continuing individual, store and controls.
The creature was explicitly started following the owner request to view it running.

A transient user service keeps the process independent of the terminal session:
`systemctl --user status creature-brain-habitat`
`systemctl --user stop creature-brain-habitat`
The service is not installed for boot. Restarting the application restores the
individual paused; Run resumes it. The LAN address can change with network setup.

Launch command (from the companion-v1 directory):
`PYTHONPATH=src .venv/bin/python examples/persistent_individual/habitat.py --home runs/habitat-visual-qualification --port 46341 --lan-address <lan-ip>`

The opt-in LAN listener binds only the chosen private interface address, while
loopback remains separate. Each listener checks its own Host and same-origin POST
header. LAN clients can use the habitat controls; no public tunnel or router
forwarding was configured. Browser rendering, live movement and saved progression
were verified at the LAN URL from this computer. Actual phone access remains
unverified. Before/after state, checks and screenshot are in validation/lan-access/.

## Diagnosed phone access failure

Kernel logs on 2026-11-08 confirm UFW blocks inbound TCP connections from
<lan-ip> to <lan-ip>:46341 on enp7s0. The service and local HTTP
response are healthy; a local HTTP test did not establish remote reachability.
The required LAN-only rule is:

`sudo ufw allow in on enp7s0 from <lan-ip>/24 to <lan-ip> port 46341 proto tcp comment 'Creature habitat LAN'`

This rule has NOT been applied: the execution environment has no-new-privileges
set and sudo cannot elevate. Owner execution from a normal desktop terminal is
required. Preserve the firewall; do not disable it. After applying the rule,
verify actual phone loading and controls at the original URL.

## Private Tailscale route installed

Use https://<tailnet-host>:46342/ with the phone connected to
the same Tailscale network. Serve proxies to loopback port 46341; no Funnel
(public internet sharing) was enabled for 46342. Existing routes were verified
unchanged. The application accepts this exact HTTPS origin only through its
loopback listener, with foreign origins still rejected. Desktop browser, HTTPS
assets/state and same-origin POST were verified; physical phone use is pending.

The user service has a 10-tailnet.conf drop-in adding --proxy-origin. Original
checkpoint and running intent were preserved on restart. Evidence is in
validation/tailscale-access/. To remove only this route:
`tailscale serve --https=46342 off`. Do not reset global Serve configuration.
The LAN UFW rule remains unapplied; Tailscale provides the alternate route.
