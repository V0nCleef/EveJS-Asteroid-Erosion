# Asteroid Erosion 0.2.3 local compatibility verification

Checked 9 November 2026 against actual EveJS 261108.1 archive/staging source.
Archive SHA256: 373266a05fd9acf0c220d06d5469907637a6d09bf2cf926adf4aaee97a3ccc59.
All eleven reviewed native files matched their archive entries byte-for-byte.

0.2.2 rejects the changed mining hooks and expects a false login signature;
261108.1 sends integer zero. 0.2.3 adds exact hashes for reviewed source and
accepts either of those two signature values without converting it. Unknown
source and other signature values still reject. The standard GridCheck
client-agent v1 patch has a separate reviewed exact 261108.1 handshake hash.

Executed candidate checks:

- 27 server checks against 261108.1 source: real native mining methods, history,
  grid membership, dispatch and marshal encoding. A 64-bit rock ID reaches two
  ready observers once; distant/unready/disconnected sessions are excluded.
  Failed delivery keeps native recovery; membership changes apply at flush;
  removed rocks get no stale radius. Terminal effect/removal share a native stamp.
- Failed persistence preserves cached stock/radius with no publication. A
  disk-backed repository fixture reloads the native scene with saved quantity
  and radius and never resurrects depleted ore. Actual database storage is
  replaced by this isolated repository fixture.
- New native gas scaling and ice presentation match unmodified source.
  Homefront/dungeon stock, waste and depletion notifications keep native semantics.
  Erosion does not patch upstream belt generation, geometry or asteroid IDs.
- Actual native login replay preserves integer signature, surrounding fields,
  client IDs and close notices. Planned GridCheck client-agent source retains
  both wrappers. This is an isolated replay, not a client launch.
- 42 client-effect and 12 settings checks pass on unchanged client files,
  including all four finishes, dust, Python 2 parsing and preference behavior.
- Existing public runtime checks and ten release-builder checks pass.

No full server, retail client, multiplayer gameplay, GPU rendering or sustained
load run was performed for this candidate yet. GridCheck runtime qualification
awaits the shared exclusive slot. Installed GridCheck 0.3.6 headless tee has no
SetBallRadius handler and cannot qualify radius visuals. Real-client companion
delivery, mining shrink/dust, depletion, preference persistence and re-entry
remain required runtime observations.

config.json, all four client files, radius rules, runtime publisher and loader
are unchanged from 0.2.2. Launcher updates still preserve config.json. Integration
must retain the actual existing config and use the guarded Launcher transaction
or equivalent, updating only Erosion's current registry fingerprint. No live
data changed during candidate preparation. This candidate is unpublished.
