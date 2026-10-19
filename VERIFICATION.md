# Asteroid Erosion 0.2.1 compatibility verification

Checked2026-10-19 against actual261018.1 source and retained0.12.9 seams. Existing mining hashes remain; the new reviewed login full-file hash is c84cffe20c00cf075a97daa31ca53c435af4f14c814e46d828760dbbb55fb566. The version-only veto was removed; unknown source edits remain rejected. Actual new login source composes with the staged AutoMining hook in either order. All client files, radius rules and persistence semantics are unchanged.

The compatibility task passed12 server boundary checks,42 client replay checks and12 UI checks; four affected source/version guard checks were rerun after removing the version veto. The isolated official updater preserved the mod and its settings byte-for-byte. These checks do not claim a new GPU rendering or multiplayer gameplay test.

Previous release verification follows unchanged as historical evidence.

# Asteroid Erosion 0.2.0 verification

Checked on 2026-10-12 against EveJS 0.12.9 Native, EVE client build 3396210,
Launcher 1.0.69, and GridCheck 0.2.0 at commit
`6953e8033008e77a511d85ad6b1613bc865bdb6b`.

All test services, accounts, data and client settings used disposable fixtures.
The live Launcher installation, live mod, existing clients and original
GridCheck playground configuration were preserved.

## Focused source and native-contract checks

- **9 server checks:** volume scaling and configuration limits; exact owned
  source validation; ready/visible observer eligibility; 64-bit asteroid IDs;
  ice/gas exclusions; actual native mining delta with waste; saved remainder;
  native targeting/drone depletion cleanup; login codec and composition with
  AutoMining and NPC Market Buyers; exact reviewed GridCheck handshake acceptance
  and rejection of changed source.
- **42 client-contract checks:** native applied radius smoothing; all four
  depletion styles; native burn effect and timing; duplicate terminal/release
  events; personal preference capture; instant shrink/final finish; character
  changes and disconnect; dust geometry, density, native property ownership,
  buffer binding, material parameters, lifetime, reuse and limits; lingering
  final dust; off-center models; complete coarse surface-angle coverage;
  private RNG; diagnostics; preference validation, per-character persistence
  and failed-read/write handling.
- Release fallbacks explicitly cover unavailable native position curves and
  failed dust cleanup. Optional particle failures cannot skip native release.
  An inline scheduling failure cannot call native release twice.
- Native depletion invalidates the removed ball's position curve to
  `(0, -3.402823466e38, 0)`. A real-client replay reproduced valid, emitting dust
  at that invisible position. Dust/quiet finishes now create a native client-side
  anchor before removal, retaining the departing model and final cloud through
  the shrink and particle lifetime. Native explosion code uses the same anchor
  API. Regression checks invalidate the original ball, verify the stable cloud
  position, and require exactly-once anchor cleanup through its owning park.
- **12 UI replays:** draft/apply/reopen; save failure and retry; dependent
  controls; native callback shapes; no accidental checkbox persistence; close;
  queued Apply after close or character change; generation/identity guards;
  window ownership after native UI refresh; strong retention of callbacks for
  native weak-reference slider signals.
- All four client Python files parse under the client's Python 2 grammar.

Client replays execute reviewed native Michelle methods with simulated rendering
and scheduling. They establish contracts and failure handling, rather than
rendered appearance or frame rate.

## GridCheck Native integration

A fresh isolated Native tree uses separate ports and newly created accounts.
The actual mining loader attaches during normal server startup.

- A fitted Miner II executes the native mining cycle and reduces ore and radius.
- Explicit mined quantity plus waste changes the remainder and cube-root radius.
- Miner and observer receive their respective native mining notifications through
  the HTTP gateway drain.
- Rebuilding the scene mining cache preserves the partial quantity and radius
  without compounding the shrink.
- Server startup restores full belt ore and radius. This is intentional native
  downtime replenishment: `resetPersistedBeltAsteroidState` runs at bootstrap.
  A failed expectation of restart persistence was corrected after reading that
  native contract; the mod does not suppress regeneration.
- Native depletion removes the exhausted asteroid and its targeting state.

This GridCheck fork intentionally suppresses `DoDestinyUpdate` for browser
sessions. HTTP mining-notification receipt does **not** establish asteroid
radius receipt. Native EVE ballpark checks are required for that boundary.

## Rendered client validation

The final candidate starts through normal client login with the Launcher's
shared MODS bootstrap and a separate settings profile. The actual MODS registry
callback opens the native window; controls are not injected by the test.

- **16 native UI/settings checks** cover opening, rendered controls, slider
  drag/end signals, Apply, reopening and saved choices after a client restart.
- Default, expanded and minimum-size layouts render with scrolling content and
  a reachable footer. The first native check exposed a zero-width scrolling
  body; explicit top-aligned content fixes it. A second check caught native
  weak-reference slider callbacks being collected; retained callbacks fix it.
- **6 native mining checks** cover received ballpark radius changes, matching
  model scale, scene-attached valid dust systems/emitters, nonzero surface
  distribution, dust size scaling and cleanup.
- **24 final-candidate finish checks**, six for each mode, cover dust, quiet,
  burning and burning with dust. Native models release and custom dust clears;
  burning modes retain the original native effect and timing.
- A nine-frame final depletion capture uses default dust strength with mining
  dust switched off. The radius-500 model shrinks through approximately 481,
  358 and 115 before release. Screenshots show the shrinking remnant and then
  the lingering dust cloud after the model disappears. Its native anchor stays
  finite while the original ball's curve is invalid; the dust and anchor are
  both cleaned up after the tail.

These checks exercise the rendered native client, rather than inferring
appearance from successful server sends or particle configuration alone.

## Launcher updates and future releases

**11 isolated production-Launcher checks** pass: package inspection/import;
synthetic next-version discovery and metadata validation; actual Qt cancel;
tampered ZIP rejection; running-server guard; changed preservation-contract
rejection; enabled and disabled updates; byte-exact custom `config.json`
preservation; unrelated file hashes; activation failure rollback; and legacy
0.1.6 migration with explicit configuration restoration. Immutable builder
re-runs and refusal to overwrite changed same-version bytes are also checked.

**10 portable release-tool checks** pass. The portable ZIP, metadata and checksum
files match the production-helper-backed local builder byte for byte. The
sidecar schema matches the Launcher's metadata helper; line endings are
canonical LF.

Every tag release requires version-specific notes and the declared update,
settings preservation, menu and minimum Launcher contracts. Its workflow uploads
all three assets to a draft, verifies GitHub asset names/sizes/digests, downloads
and compares their exact bytes, and only then publishes. Published versions are
never replaced. The final archive is checked again with the real Launcher before
the tag is pushed; hosted discovery/download is checked after publication.

## Evidence limits

The user accepted 0.1.6's dust appearance after earlier video-guided revisions,
and previously confirmed asteroid shrinking on two clients. The linked 0.1.6
demo is historical appearance evidence, not a demonstration of the new menu.

No automated check establishes every GPU, camera distance, localization, other
mod combination, or sustained high-load frame rate. Dust remains bounded to
384 particles per active rock and 1–64 active rocks. Source research, proprietary
client references, credentials, private fixtures and local receipts are excluded
from the public package.
