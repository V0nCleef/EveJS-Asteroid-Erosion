# Asteroid Erosion

Ore asteroids shrink as you mine them, shedding dust that scales with the rock.
Choose how they finish: dust and crumble, EVE's original burning effect,
burning with dust, or a quiet final shrink.

**Version 0.2.2 local compatibility repair · EveJS 0.12.9 / 261018.1 / 261028.1 Native · EveJS Launcher 1.0.69 or newer**

This local package is unpublished. On 261028.1, radius updates use the native
tick history and bubble batches. Older supported releases retain their original
delivery path. Settings, personal depletion styles and client effects are unchanged.
See [VERIFICATION.md](VERIFICATION.md) for the checks and their limits.

The previous public release is [0.2.1](https://github.com/V0nCleef/EveJS-Asteroid-Erosion/releases/tag/v0.2.1).
Use the supplied local `AsteroidErosion-0.2.2.zip` for this repair.

## Install

1. Close EVE clients and stop the Game server.
2. In EveJS Launcher **Mods → Add ZIP**, select `AsteroidErosion-0.2.2.zip`.
3. Enable **Asteroid Erosion**, start the Game server, fully reopen the clients,
   and log in.
4. Open the in-game **MODS → Asteroid Erosion** menu.

The companion and shared menu are delivered during login. Connected clients
need a full restart to receive a new version.

### Upgrading from 0.1.6

0.1.6 has no update provider, so this upgrade needs one manual migration:

1. Close clients, stop the Game server, and copy the old mod's `config.json`
   somewhere safe.
2. Remove the old Asteroid Erosion through the Launcher. The Launcher retains
   its quarantine copy; keep your backup too.
3. Use **Add ZIP** to import 0.2.2. Leave it disabled while restoring your saved
   `config.json` into the newly imported mod folder.
4. Enable it, start the server, and fully reopen the clients.

Importing another ZIP alone does not migrate the old configuration. Avoid
leaving two versions of the same mod installed.

### Updates from 0.2.0 onward

Use the Launcher's mod update controls for subsequent releases. The package
declares its GitHub update source and preserves `config.json` during updates.
Personal visual preferences stay in EVE's own per-character client settings.
Close clients and stop the Game server before applying an update, then fully
restart them afterwards.

Every release must contain the matching `AsteroidErosion-<version>.zip` and
`AsteroidErosion-<version>.update.json`. The repository's tag release workflow
builds both together, validates their contract, and publishes them with SHA-256
checksums. Missing metadata or a changed preservation contract fails the build.

## In-game settings

Controls edit a draft. **Apply** saves it; closing without applying discards
the draft. Settings apply to this character in this client profile, including
after reconnecting or updating the mod. They do not change ore quantities,
physical radius, mining yield, or other players' visual preferences.

| Finish | Behaviour |
| --- | --- |
| Dust & crumble | Final remnant shrinks away beneath lingering dust. |
| Burning | EVE's original burning dissolve and its native 33-second timing. |
| Burn + dust | Original burning dissolve with an additional surface dust burst. |
| Quiet finish | Final remnant shrinks away without depletion dust. |

The menu also controls surface dust while mining, dust strength, smooth
shrinking, and shrink time. **Fine tuning** contains dust lifetime, final shrink
time, and the maximum number of dusty rocks. Burning modes keep EVE's native
timing; the final shrink slider applies to the other two finishes.
The mining dust checkbox and final depletion dust are independent. Dust
strength zero suppresses all dust. Applied changes affect the next shrink or
depletion; an animation already in progress keeps its captured settings.

## Mining behaviour

- Radius follows `original radius × (remaining ore / original ore)^(1/3)`.
  At 12.5% ore remaining, the radius is half its original value. Waste counts.
- Nearby ready observers receive native radius updates. NPC and drone mining
  use the same authoritative state. Native persistence supplies the saved size
  to newly loaded rocks during the session. EveJS replenishes belt rocks at
  server startup, matching its normal downtime behaviour.
- Physical radius and mining range follow the current radius. A ship may need
  to move closer as the surface recedes. Smoothing only affects presentation.
- At zero, the server performs normal depletion, targeting, and drone cleanup.
  The selected finish controls only the departing client visual.
- Dust follows the rendered model's size and center. Twelve overlapping surface
  regions vary the puffs, and particles already shed keep drifting.
- Ice, gas, and ordinary grid/warp removals keep native behaviour. A client
  without the companion retains its native depletion effect.

Dust is bounded to 384 particles per active rock, with a default maximum of 24
rocks and an adjustable limit of 1–64. Higher limits can cost more GPU time.
Grid departure, character changes, and disconnect clean up owned effects.

## Server configuration

Edit `config.json` while the Game server and clients are stopped, then restart
them. These values supply initial visual defaults; saved personal choices take
precedence for the visual controls.

| Setting | Default | Purpose |
| --- | --- | --- |
| `radiusExponent` | `1/3` | Volume-consistent radius; `0.5` exaggerates shrinking. |
| `minimumRadiusRatio` | `0.005` | Minimum radius as a fraction of the original. |
| `minimumRadiusMeters` | `2` | Minimum server radius, capped at the original. |
| `resizeDurationMs` | `600` | Initial visible resize duration, 0–3000 ms. |
| `depletionDurationMs` | `650` | Initial final shrink duration, 0–2000 ms. |
| `dustEnabled` | `true` | Initial mining dust choice. |
| `dustIntensity` | `1` | Initial dust strength, 0–3. |
| `dustLifetimeMs` | `1400` | Initial dust lifetime, 300–4000 ms. |
| `dustMaxConcurrent` | `24` | Initial active dusty-rock limit, integer 1–64. |

The first three settings are authoritative server rules and are deliberately
absent from the personal menu. Native ore persistence is unchanged.

## Compatibility and removal

Supports **EveJS 0.12.9 and 261018.1 Native** and the reviewed EVE client build 3396210.
The loader validates its owned mining hooks and the login builder, composes
incoming source in memory, and refuses unsupported hooks. Login delivery
composes with AutoMining and NPC Market Buyers. Core files and client archives
are never rewritten. Dust uses a resource already shipped with EVE.

Disable/remove the mod with clients and server stopped, then restart them.
For standalone Native use, preload `loader.js` before `server/index.js`:

```powershell
node --require ./mods/AsteroidErosion/loader.js ./server/index.js
```

The shared **MODS** menu requires Launcher's client-menu bootstrap; loading the
server mod alone does not provide that menu.

## Diagnostics and verification

Server logs show `Native login companion attached` and
`Ore radius and observer updates attached`. Client marker:
`ASTEROID_EROSION:READY:0.2.0`.

The per-profile cache contains `asteroid-erosion.log`, including with
`/noconsole`. `DUST_READY`, `DUST_UNAVAILABLE`, and bounded `DUST_STATE` samples
describe setup and native validity. A setup marker alone does not prove visible
rendering. See [VERIFICATION.md](VERIFICATION.md) for tested coverage and limits.

## Gameplay demo

[![Asteroid Erosion 0.1.6 gameplay preview](https://raw.githubusercontent.com/V0nCleef/EveJS-Asteroid-Erosion/v0.1.6/docs/demo-preview.gif)](https://github.com/V0nCleef/EveJS-Asteroid-Erosion/releases/download/v0.1.6/AsteroidErosion-0.1.6-demo.mp4)

V0nCleef's accepted **0.1.6 dust appearance**. This older recording does not
demonstrate the new settings menu or burning options.
[Original MP4](https://github.com/V0nCleef/EveJS-Asteroid-Erosion/releases/download/v0.1.6/AsteroidErosion-0.1.6-demo.mp4).
