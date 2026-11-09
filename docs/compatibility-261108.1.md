# EveJS 261108.1 compatibility: Asteroid Erosion 0.2.3

This update supports EveJS **261108.1 Native**, alongside 0.12.9, 261018.1 and
261028.1. It retains the Launcher API/menu contract and minimum Launcher 1.0.69.

The release adds exact reviewed hashes for the updated native mining hooks and
login source. The login companion accepts the new integer-zero signature while
preserving it. Unknown source changes still fail closed. Native persistence-first
failure handling and the new gas cloud curve retain their upstream behavior.
The radius algorithm, history publisher and all four client files are unchanged
from 0.2.2. The standard GridCheck client-agent patch has its own exact source hash.

Upstream archive SHA256:
`373266a05fd9acf0c220d06d5469907637a6d09bf2cf926adf4aaee97a3ccc59`.
All eleven reviewed native files matched that archive byte-for-byte.

Fresh checks on 9 November 2026:

- 27 native/source checks, 42 client-effect checks, 12 settings/UI checks,
  12 public runtime regressions and 10 release-tool checks passed.
- The actual retail client used a native mission-ore site with 333 units of
  Augumene, an existing Ibis and Civilian Miner, and no skill or loadout grants.
- After 178 units were mined, 155 remained. Expected radius was 387.494752746 m;
  actual client radius and rendered model scale were both 387.494750977 m.
  Bubble exit/re-entry retained the same rock ID, remainder and size.
- Final native ledger and cargo quantities were both exactly 333. The durable
  dungeon remainder reached zero and the actual client removed the rock. Thirty
  sampled frames had active dust; the terminal sample retained one dust effect
  after the rock disappeared. No current-run Erosion resize/particle failure was
  recorded.
- A full server and client process restart kept the same world. Zero stock,
  absent rock and all 333 cargo units persisted. Saved visual preferences survived
  the restart, then original test-profile preferences were restored and saved.
- The final real-client ballpark comparison matched: server 107, client 107,
  shared 107, no mismatch. The four-mod configuration and Erosion payload stayed
  byte-identical during qualification.

The first 141 units came from a copied AutoMining preference colliding with the
fresh lab character ID. That job was stopped; subsequent partial-cycle and final
depletion checks used manual native controls on the same finite rock. This was a
lab fixture deviation, with no played-world state reset or modification.

Scope is precise: default dust finish and single-client ore gameplay were tested
live. Burn/hybrid/quiet and two-observer routing retain focused/source coverage.
The cold process restart was performed after depletion; the half-mined remainder
was checked through durable state and re-entry, not a separate half-mined restart.
Natural-belt generation/migration was reviewed but did not receive a separate
full natural-belt gameplay/restart run. The post-restart exception ring was clear;
the pre-restart ring was not exported, so this is not a claim of zero exceptions
across every client subsystem.

The installable artifact is frozen to the qualified bytes:

`AsteroidErosion-0.2.3.zip` — 84,419 bytes — SHA256
`9b6f42f4f10d3f9bbf5beada58edeeee3feb0ebd3f47278fcaffaea7b5e7ae75`.

Its embedded preparation-time status was preserved to avoid repacking a tested
artifact. Current release status and later verification live in this document and
the versioned release notes, outside the ZIP. Launcher updates from 0.2.0 onward
preserve `config.json` and the existing per-character visual preference key.
