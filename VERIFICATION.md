# Asteroid Erosion 0.2.4 candidate verification

Target: EveJS 261115.2, archive SHA-256
899ca7dd19abd4d9441966a60bbecc37008b459284c0601ae2af8edc29271be0.
Reviewed against actual archive source on 16 November 2026. Base mod: public
0.2.3, commit 9953e7f4c390587c7ce9ea289866d329e435995a.

The presentation hook now honors native miningFixedRadius === true. The
new stock handshake adds staff-only health delivery; its integer-zero signature,
expression envelope and outgoing packet method remain unchanged. Exact hashes
are added only after review. Unknown source still rejects. The exact 261115.2
handshake with GridCheck 0.3.6's two client-agent v1 insertions is reviewed and
accepted separately; the coordinator's actual runtime must match those bytes.

Focused checks execute the actual 261115.2 mining functions, native tick history,
bubble routing, batch dispatch and marshal codec with isolated stores and sockets.
They cover mined/waste stock, fixed-radius preservation and native depletion,
partial/depleted repository reload, failed persistence, observer transitions,
server-only anchors, stale updates, native gas/ice, Homefront and dungeon writes.
Native login replay covers the health-window role gate and preserves the original
expression and packet fields. Companion composition is checked with installed
AutoMining and NPC Market Buyers delivery modules in memory.

Client effects and settings tests use fixtures and Python-2 syntax checks; they
do not establish current GPU rendering. Release-builder checks enforce the ZIP,
sidecar, checksums, native-only backend, menu and config preservation contracts.
Detailed results and exact commands are in the task's report.json and evidence/.

Mandatory remaining gates: actual new-version GridCheck server/client mining,
model radius/dust, partial and depleted stock across same-world cold restarts,
login/menu and saved preferences, and combined-mod coverage. A headless tee
without SetBallRadius cannot qualify visuals. No full stack or retail client was
started during candidate preparation. Historical 261108.1 runtime results do not
qualify 261115.2. Docker is not declared or runtime-qualified.

config.json, client files and personal preferences are unchanged. Integrate only
through the guarded Launcher transaction/equivalent ownership checks and retain
the existing config, save state and effective enabled state. No live files,
databases, Launcher source or physical client were changed. Unpublished candidate.
