# Asteroid Erosion 0.1.6 verification

Verified on 2026-10-10 against the installed EveJS 0.12.9 source and EVE client
`code.ccp` SHA-256:

`9152856eed37fd1159beee5894b60d22bd0b9e36df2eb7215dc5f1dc7eb80949`

## Automated evidence

- Eight focused Node checks: volume scaling and limits; owned-function source
  validation and composition; all materialized ready observers; preservation
  of 64-bit asteroid IDs; ice/gas exclusions; native source-less NPC mining
  deltas with waste; saved remainder; native final depletion, targeting and drone
  cleanup; native packet encoding, login composition and visibility eligibility.
- Twenty-two client-contract replays: applied radius resizing; final-cycle dissolve
  replacement and one release; ice exclusion; ordinary grid removal; overlapping
  resize cancellation; disconnect during final animation; dust sizing and particle
  lifetime/budget; lingering dust after a large final cycle; effect reuse and
  concurrency limits; immediate cleanup on grid departure; disabled/missing dust;
  strict native property ownership for mesh bounds; persistent client diagnostics;
  buffer rebuild before emitter binding and scaled material fade; emission state
  initialized before scheduling expiry; bounded native-state diagnostics;
  model bounds and off-center geometry; puff overlap, drift and mesh containment;
  invalid bounds fallback; final cloud position after native model-curve cleanup;
  complete coarse surface-angle coverage with one emitter and bounded capacity; repeatable plume
  layouts per rock/burst without modifying the client's global RNG.
- The client replay executes the installed client's decompiled
  `Park.RealFlushState`, `SetDestructionEffectOnRemove`,
  `TerminalPlayDestructionEffect` and `RemoveBalls` methods, converted to
  Python 3 for the harness. Rendering and task scheduling are simulated.
- Companion parses under the Python 2 grammar used by the installed client.
- Real Launcher ZIP inspection, import, mod scanning, enable, disable and remove
  pass in an isolated folder using the current Launcher source.
- The real native login codec preserves the existing login payload. AutoMining
  payload composition and NPC Market Buyers packet wrappers work in both orders.
- The native `spaceMgr` removal path calls the object's `Release`, confirming
  the companion's final animation hook is on the installed removal path.
- Native `GenericEffect.ShipEffect` supplies the reviewed `EveEffectRoot2`,
  `effectChildren`, `translationCurve` and scene insertion/removal pattern.
- The shipped `as2_l_01_dust_v2.black` is a lit asteroid particle effect with
  sphere emitters, lifetime and size generators, and a camera-display curve.
  Its SHA-256 is `35cec09eb2d34180f5bd8cb052ca3942376f28b0b609c175511811b2552470ed`;
  its MD5 matches the installed client index. Its large environment dimensions
  are replaced with the current rock radius; lifetime and particle count are
  bounded, and the original camera-display driver is removed from this instance.

The checks use isolated state and controlled fixtures. They do not start the
server, run the universe, or connect a game client. Proprietary client code and
research dependencies are excluded from the ZIP.

## User-reported gameplay evidence

On 2026-10-09 the user confirmed that 0.1.0 shrinks the asteroid on both clients.
They also reported a visibly substantial final remnant disappearing when a
remaining 17k volume was depleted. The new final dust burst is intended to cover
that transition, starting at the pre-depletion visible size.

The user then reported no dust during either shrinking or depletion on 0.1.1.
Read-only inspection of the installed resource showed that `Tr2ParticleSystem`
ends at offset 2213, followed by `minBounds` and `maxBounds` properties belonging
to its parent `Tr2InstancedMesh`. Native `trinutils.particlebounds` likewise writes
these properties on meshes. 0.1.1 instead attempted to write them on the particle
system, inside a block that disables dust on setup failure. A strict-property
replay reproduced the missing effect before the fix and passes after moving the
bounds writes to meshes. This is a verified implementation defect; the original
live client exception was not captured by its console-only diagnostics.

0.1.2 adds per-profile `cache:/asteroid-erosion.log` with setup stage and exception
details, plus a first-effect marker. It keeps the same shrink and dust dimensions,
timing, particle limits and server behavior.

The user's 0.1.2 recording still shows no visible dust during shrinking. Both
live client logs contain `DUST_READY:radius=500.000:particles=96`, with no setup
exception. This proves setup completed, not that particles spawned or rendered.

The installed effect's decoded BLACK graph contains a source brightness of
0.1167201 and a particle shell radius of 199487–230000 with 250000-unit sprites.
Our 0.1.2 sprites were comparatively much smaller, and its 0.85–1.02 radius shell
placed emission partly within the rock's nominal radius. The native compiled
shader's metadata labels `ParticleParams.xy` Fade Near/Far Distance; its DXBC
multiplies RGBA by `saturate((abs(viewDepth)-near)/(far-near))`. The original
250 m fade can suppress close views. These are plausible visibility problems,
not a verified single root cause of the user's recording.

0.1.3 uses a 1.05–1.18 radius shell, sprite diameter 0.25–0.50 radius, brightness
0.8 and far fade 0.01 starting radius (0.01 m floor). Native packaged
`trinity.particlesystemelements.Link` and the particle validators establish the
`UpdateElementDeclaration` then `Rebind` sequence now used after capacity edits.
Native `evegraphics.effects.SetParameterValue` establishes the const-parameter
tuple replacement and `RebuildCachedData` material update pattern. Particle mesh
areas are explicitly displayed after removing their camera curve. Expiry begins
only after rate and deadline initialization. Up to eight burst diagnostics read
native validity and optionally exposed instance counts, with unavailable counts
reported explicitly. Those changes are checked by controlled fixtures; their
rendered effect remains unverified.

The user's 0.1.3 recording confirms visible, sparse dust detached from the rock.
Both native client logs show valid particle systems and no setup failure.
The configured shell extended to 1.18 nominal radius with speeds up to
0.45 radius/s; puffs could move another 0.63 radius during their default lifetime.
These values and the clip support changing presentation, but do not establish
the exact rendered mesh-to-nominal-radius ratio.

0.1.4 uses the installed `GenericEffect.ShipEffect` model-bound APIs:
`GetBoundingSphereRadius()` for sizing and `EveLocalPositionCurve(centerBounds)`
for centering. Its ratio to modelScale is sampled once per burst and applied to
future emissions during the animation, without rescaling particles already shed.
The shell is 0.72–0.96 visible radius, billboard size 0.90–1.35 radius, speed
0.035–0.09 radius/s, rate 218–320/s at default intensity and capacity 192/rock.
The mesh bounds contain the full configured drift and billboard half-diagonal.
Native `SpaceObject._Clearcurves` clears model translation on release, so final
dust snapshots its center offset using the native curve GetVectorAt contract and
`Tr2TranslationAdapter` before falling back to the retained ball position curve.
The replay covers an off-center model with 0.35 rendered-to-nominal size, repeated
shrinking, invalid bounds, and native-style clearing of the model position curve.
This is contract and geometry evidence, not a native rendering measurement.

On 2026-10-10 the user supplied a recording of 0.1.4 and reported that it looks
much better, but too round. The contact sheet shows visible dust surrounding the
rock in a roughly circular cloud during two shrinking cycles. This establishes
visible dust in that clip, not multi-client or final-depletion coverage.

0.1.5 restricts the existing sphere generator's Phi/Theta angular windows to
three broad patches. The same emitter switches patches at 90/155/260 ms within
each repeating 260 ms interval; no extra emitter or task is added. A private RNG
produces repeatable angles, sizes and speeds for each rock and observed burst.
Billboards vary independently in width and height and are smaller than in 0.1.4;
model-based center/radius, brightness, rate, lifetime, capacity and release
handling are retained. Angle interpretation is corroborated by the primary
[CCPWGL2 sphere-generator implementation](https://github.com/cppctamber/ccpwgl2/blob/master/src/particle/generators/Tw2SphereShapeAttributeGenerator.js).
The native source asset already serializes the same generator and `maxPhi`.
Controlled checks verify angular gaps, proportional dimensions, shared budget
and private RNG behavior. Native appearance of the new plume layout is unverified.

The user's next 2026-10-10 recording shows three separated dust clouds and bare
regions between them. 0.1.6 replaces those windows with twelve overlapping
regions: three latitude bands, each spanning all four azimuth quadrants. A
shuffled, repeatable visit order alternates regions on each animation step;
clock-based selection is removed to avoid sparse angular sampling at longer
configured resize durations. Puff width, height, density, radial extent and
drift vary across regions. Base emission is 453–640/s at intensity 1, modulated
by 0.85–1.15 per region, with capacity increased from 192 to 384. This is roughly
twice the previous emission and capacity. The existing coverage check now
verifies all 63 combinations of seven polar and nine azimuth sample directions,
alongside proportional sizing, one emitter and bounded capacity. These checks
do not establish native frame rate or rendered coverage. The user subsequently
accepted the 0.1.6 appearance in game and supplied the release demo recording.
Performance has not been separately measured.

## Further in-game checks

1. Import/enable the ZIP, restart the Game server and fully restart EVE clients.
2. Verify both server attachment messages and client
   `ASTEROID_EROSION:READY:0.1.6` and first-effect `DUST_READY` in its cache log.
3. Mine an ore rock through several cycles: verify smooth shrinking and scanner
   quantities, dust at the surface, and smaller puffs from smaller rocks. Then
   exhaust it: verify a final shrink covered by lingering dust without burning.
4. Observe the same rock with a second client, and warp away/back or reconnect
   after partially mining it: verify the matching saved size.

The user confirmed that 0.1.6 looks good and provided the 18.7-second release
demo on 2026-10-10. This establishes user acceptance of the displayed effect.
Full multi-client dust, camera/laser attachment edge cases, and performance
remain unverified. The client-contract replay simulates
particle properties and scheduling; it cannot prove rendered appearance or FPS.
Saved-size reconnect and joint live gameplay with other mods remain unverified.

The ZIP is built and checked separately before installation. Installation
receipts and rollback backups are kept outside this public package. No running
service is stopped or restarted by the build or verification scripts.
