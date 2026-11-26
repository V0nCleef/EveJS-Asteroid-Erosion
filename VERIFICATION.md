# Asteroid Erosion 0.2.5 verification

Reviewed on 26 November 2026 for EveJS 261125.3 and 261126.2 Native with
EVE client 24.02 build 3724492. Base: public 0.2.4, commit
6c33d2d591edc8c037f99dc6415bfe1fb9301934.

This release changes compatibility metadata and documentation. Runtime JavaScript,
configuration and all client Python files remain byte-identical to 0.2.4.
The exact-source checks for mining and login are unchanged and still reject
unknown source. Previous version declarations and settings preservation remain.

Sixteen of the seventeen reviewed mining, scene, notification and wire modules
match the 261115.2 baseline. The 261126.2 scene presentation change delivers a
docked structure observer's initial state immediately; the terminal asteroid
effect and static removal methods are unchanged. Ordinary observer radius
updates continue through native tick history and bubble batches.

Focused checks execute actual server source with isolated repositories and
session I/O: 35 pass on 261126.2 and 35 pass on the 261115.2 regression baseline.
Three retired-installation checks are explicitly skipped. Coverage includes ore
and waste conservation, sequential shrinking to two observers through native
marshal encoding, final depletion, fixed-radius mission rocks, failed persistence,
repository reload, native gas/ice, visibility and login composition. Repository
fixtures do not establish real SQLite or full-process restart behavior.

The exact shipped 3724492 code archive was compared with 3396210 across 21
selected modules. Asteroid assembly/model scaling and the Carbon UI controls
used here are unchanged. The relevant dispatch, effect assignment, ball removal
and anchor methods retain their APIs. Native release adds global-object cleanup;
native DISSOLVE remains effect 2 with 33-second timing. The dust resource is
byte-identical across builds and matches both resource indexes.

Client effects/preferences replay passes 42 checks against the exact new client
methods and 42 against the old methods; three controlled native release checks
and twelve menu/settings fixtures pass. These use converted Python methods and
fake engine/model/scene objects, not a running retail client. The shared MODS
menu still requires the Launcher's bootstrap.

The new client Destiny, Trinity and Python native binaries differ. Actual
3724492 model/dust rendering, native bindings, combined-mod retail reconnect,
and partial/depleted mining across full cold restarts remain live acceptance
limits. No new live gameplay test is claimed. The earlier 0.2.4 Windows runtime
qualification applies to its earlier stack only. Linux/Wine/Proton and Docker
are not newly qualified; the manifest continues to declare only Native.

The release builder validates the exact ZIP whitelist, stable version, matching
updater sidecar, checksums, config preservation and menu contract. Publishing
requires complete uploaded assets and a byte-for-byte download verification.

For an update, close EVE and stop the game server first, update in the Launcher,
then fully reopen EVE to receive the companion. `config.json` and native
per-character visual preferences are retained; no save migration is required.
