# EveJS 261028.1 compatibility

Asteroid Erosion 0.2.2 was locally installed and checked on 29 October 2026.
Publication was authorized on 30 October after the user reported that Erosion
and the other updated mods seem to work in gameplay. This report is separate
from automated evidence and is not a controlled multiplayer or rendering test.

The actual 261028.1 scene removed `sendDestinyUpdates`. The old publisher could
therefore return without publishing an intermediate radius change; its old
`sendOptions.js` dependency was not reached on that path. The companion and
native terminal-depletion path could still work, consistent with the user's
observation. A replay of the old publisher against the new scene API reproduced
the intermediate-update drop.

The repair queues one `SetBallRadius` through `queueBallHistory`. Native tick
routing owns the stamp, current bubble membership, batch encoding and failed-send
recovery. The old helper is resolved only where it exists for older supported
builds. No removed EveJS core module is restored.

The local evidence comprises 22 server/native-boundary checks, 42 client replays,
12 UI replays, 14 focused 261018.1 regressions and 7 focused 0.12.9 seam checks.
The native boundary replay executes actual mining, history, membership, batch
planning, dispatch and encoder source with persistence/diagnostics/session I/O
isolated. It covers two visible observers, distant/unready/disconnected sessions,
membership changes before delivery, failed-recipient recovery, terminal effects
and packaged removal on one tick. The installed loader probe also delivered a
radius change through the new native path. All four client files stayed intact.

No fresh automated full-server startup, retail/GPU rendering, Docker, extended
multiplayer combination matrix or sustained-load claim is made. Local evidence,
player state, rollback data and proprietary client references are excluded from
this repository and the release assets.

The release preserves the exact tested ZIP. Its included README and verification
file are preparation-time records, so their references to a local unpublished
candidate describe that earlier state. Current publication and the later user
confirmation are recorded in the release notes without changing tested bytes.

Portable publisher tests run with `node --test test/*.test.cjs`; native boundary
replays require `EVEJS_TEST_ROOT` pointing at a separate compatible EveJS source
fixture. The test does not start the Game server, and does not require or copy
game databases or proprietary client assets. CI runs the portable checks and
skips the native replay when no source fixture is supplied.
