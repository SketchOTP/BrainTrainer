# Grounded connection state

A disconnected view previously kept animating its last received running state.
It now freezes the sprite and explicitly labels current activity unknown, retaining
the last received moment. Controls are disabled until a fresh state arrives.
The host may still be running; disconnection is not described as a creature pause.

State reads are serialized and time out after five seconds. Commands have a ten
second response timeout, report unconfirmed outcomes and are never automatically
resent. Polling only retrieves state. Reconnection clears animation event baselines
so missed rehearsal/revision counts are not replayed as current actions. Reduced
motion and paused-save behavior remain intact.

The Node animation checks passed, including disconnect freeze and no replay on
reconnection. Browser qualification used a separate test branch: a running server
was stopped, controls disabled, the sprite remained at the same frame across
observations, and restarting the server restored the page automatically to paused
saved tick 570. The test server was stopped afterwards. Main activity was not
paused or restarted. The refreshed HTML and animation asset are served directly.

This is a display/recovery fix, not a solution to the confirmed UFW port block.
Actual phone access still requires the documented LAN firewall rule. See
LOCAL_NETWORK_HABITAT.md. Evidence is in validation/connection-state/.
