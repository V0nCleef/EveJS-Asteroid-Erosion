"use strict";

const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const { isMainThread } = require("node:worker_threads");
const { KEY, validateMiningSource, prepareMiningSource } = require("./lib/source");
const { normalizeConfig } = require("./lib/radius");
const { createRuntime } = require("./lib/runtime");
const delivery = require("./lib/delivery");
const canonical = file => path.resolve(file).replace(/\\/g, "/").toLowerCase();

function resolveRoot(start = __dirname) {
  let directory = path.resolve(start);
  for (let depth = 0; depth < 10; depth++) {
    if (fs.existsSync(path.join(directory, "server/package.json"))) return directory;
    const parent = path.dirname(directory);
    if (parent === directory) break;
    directory = parent;
  }
  throw new Error("EveJS root not found; install the mod under the server's mods directory");
}

function install(root = resolveRoot()) {
  if (!isMainThread || process.env.EVEJS_WALLET_AUTHORITY_OWNER === "1" ||
      /[\\/]server[\\/]src[\\/].*\.worker\.js$/i.test(process.argv[1] || "")) return { active: false, reason: "worker" };
  const symbol = Symbol.for(KEY);
  if (globalThis[symbol]) return globalThis[symbol];
  // Version labels are advisory. Validate the actual owned source seams below.
  const miningFile = path.join(root, "server/src/services/mining/miningRuntimeState.js");
  const handshakeFile = path.join(root, "server/src/network/tcp/handshake.js");
  validateMiningSource(fs.readFileSync(miningFile, "utf8"));
  if (!delivery.supportsHandshake(fs.readFileSync(handshakeFile, "utf8"))) throw new Error("Unsupported native login builder");
  if ([miningFile, handshakeFile].some(file => require.cache[require.resolve(file)])) throw new Error("Load Asteroid Erosion before the native mining and login modules");
  const config = normalizeConfig(JSON.parse(fs.readFileSync(path.join(__dirname, "config.json"), "utf8")));
  const warnings = new Set();
  const state = {
    active: true, root, config, miningAttached: false, handshakeAttached: false,
    warn(error) {
      if (warnings.size >= 10 || warnings.has(error.message)) return;
      warnings.add(error.message);
      console.error("[Asteroid Erosion] " + error.message);
    },
  };
  const loadNative = name => require(path.join(root, "server/src", name));
  // Legacy releases send immediately with history-safe options; 261028.1
  // queues through scene.queueBallHistory and never loads this removed module.
  const legacyOptionsFile = path.join(root, "server/src/space/destiny/delivery/sendOptions.js");
  const buildSendOptions = fs.existsSync(legacyOptionsFile)
    ? () => require(legacyOptionsFile).buildMichelleSafeDestinySendOptions()
    : () => { throw new Error("Unsupported legacy Destiny delivery: send options unavailable"); };
  state.runtime = createRuntime({
    config, active: () => state.active,
    buildRadiusPayload: (...args) => loadNative("space/destiny/stream/actions.js").buildSetBallRadiusPayload(...args),
    buildSendOptions,
    isReady: session => loadNative("space/runtime/destinyDeliveryEligibility.js").isReadyForDestiny(session),
    canReceive: (scene, session, entity) => loadNative("space/runtime/destinyDeliveryEligibility.js").canSessionReceiveEntityDependentDestinyUpdate(scene, session, entity),
    warn: state.warn,
  });
  state.delivery = delivery.createDelivery(__dirname, config);
  globalThis[symbol] = state;
  const previousCompile = Module.prototype._compile;
  Module.prototype._compile = function(source, filename) {
    const file = canonical(filename);
    if (state.active && file === canonical(miningFile)) {
      try { source = prepareMiningSource(source); }
      catch (error) { state.active = false; state.warn(error); }
    }
    const result = previousCompile.call(this, source, filename);
    if (state.active && file === canonical(handshakeFile)) {
      try {
        delivery.installHandshake(this.exports, {
          codec: loadNative("network/tcp/utils/marshal.js"),
          delivery: state.delivery, active: () => state.active,
        });
        state.handshakeAttached = true;
        console.log("[Asteroid Erosion] Native login companion attached");
      } catch (error) { state.active = false; state.warn(error); }
    }
    if (file === canonical(miningFile) && state.miningAttached) console.log("[Asteroid Erosion] Ore radius and observer updates attached");
    return result;
  };
  return state;
}

if (require.main !== module) {
  try { install(); }
  catch (error) { console.error("[Asteroid Erosion] Mod inactive: " + error.message); }
}
module.exports = { install, resolveRoot };
