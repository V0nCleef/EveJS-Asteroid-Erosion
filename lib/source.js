"use strict";

const crypto = require("node:crypto");
const KEY = "evejs.asteroid-erosion.v1";
const MARKER = "// Asteroid Erosion: reviewed mining presentation hooks v1";
const REVIEWED = Object.freeze({
  applyYieldPresentationToEntity: "c0c6358f63ee62cce6df6265c8caae24c76eab40e863395feacb8cd0d6b0b720",
  updateMineableState: "ec6269059d062b822b86cfd39838a5908b1e9904c584712d0b1810f144140b55",
});
const digest = source => crypto.createHash("sha256").update(source).digest("hex");

function validateMiningSource(source) {
  const text = String(source).replace(/\r\n/g, "\n");
  if (text.includes(MARKER)) throw new Error("Asteroid Erosion is already attached to this source");
  for (const [name, hash] of Object.entries(REVIEWED)) {
    const matches = [...text.matchAll(new RegExp(`^function ${name}\\([^\\n]*\\) \\{`, "gm"))];
    if (matches.length !== 1) throw new Error(`Missing or duplicated mining hook: ${name}`);
    const start = matches[0].index, end = text.indexOf("\n}\n", start);
    if (end < 0 || digest(text.slice(start, end + 3)) !== hash) {
      throw new Error(`Unsupported mining hook: ${name}`);
    }
  }
  if (!/^  updateMineableState,$/m.test(text)) throw new Error("Mining export changed");
  return true;
}

function prepareMiningSource(source) {
  validateMiningSource(source);
  // Append to the actual incoming source so unrelated loader edits survive.
  // Rebind both the internal function and its public export before consumers
  // can destructure it. Initialization and every native mining source share it.
  return source + `\n${MARKER}
const __aeState = globalThis[Symbol.for(${JSON.stringify(KEY)})];
if (__aeState && __aeState.active) {
  const __aePresent = applyYieldPresentationToEntity;
  applyYieldPresentationToEntity = function(entity, state, summary) {
    const result = __aePresent.apply(this, arguments);
    try { __aeState.runtime.present(entity, state); }
    catch (error) { __aeState.warn(error); }
    return result;
  };
  const __aeUpdate = updateMineableState;
  updateMineableState = function(scene, entity, nextState, options = {}) {
    const previousRadius = entity && entity.radius;
    const result = __aeUpdate.apply(this, arguments);
    try {
      if (result && result.success) __aeState.runtime.publish(scene, entity, result.data.state, previousRadius, options);
    } catch (error) { __aeState.warn(error); }
    return result;
  };
  module.exports.updateMineableState = updateMineableState;
  __aeState.miningAttached = true;
}
`;
}

module.exports = { KEY, digest, validateMiningSource, prepareMiningSource };
