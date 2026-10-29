"use strict";

// Execute the installed 261028.1 queue, bubble membership, batch planner,
// dispatch and wire encoder. Only stores, diagnostics and session I/O are
// replaced. No EveJS service is started and no player state is read/written.
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const vm = require("node:vm");
const root = path.resolve(process.env.EVEJS_TEST_ROOT);
const src = path.join(root, "server/src");
const codec = require(path.join(src, "network/tcp/utils/marshal.js"));
const grid = require(path.join(src, "space/destiny/visibility/gridBubbles.js"));
const actions = require(path.join(src, "space/destiny/stream/actions.js"));
const warnings = [];
const log = {warn: message => warnings.push(message)};

function compile(relative, override) {
  const file = path.join(src, relative);
  const compiled = new Module(file, module);
  compiled.filename = file;
  compiled.paths = Module._nodeModulePaths(path.dirname(file));
  const nativeRequire = Module.createRequire(file);
  compiled.require = name => {
    if (name !== "path" && !name.startsWith("node:")) {
      const absolute = path.resolve(path.dirname(file), name).replace(/\\/g, "/");
      const replacement = override(absolute);
      if (replacement !== undefined) return replacement;
      if (/(gameStore|tableRepository|itemTypeRegistry)/.test(absolute)) throw Error("Store access forbidden: " + name);
    }
    return nativeRequire(name);
  };
  compiled._compile(fs.readFileSync(file, "utf8"), file);
  return compiled.exports;
}

// Read the two real clientSession encoder bodies, avoiding the network class's
// store/service imports. Both fail explicitly if their source shape changes.
const sessionSource = fs.readFileSync(path.join(src, "network/clientSession.js"), "utf8");
const wrapper = sessionSource.match(/^function buildBroadcastNotificationMarshalValue\([^\n]*\) \{[\s\S]*?^\}/m);
const encoder = sessionSource.match(/^  static encodeNotificationPayload\([^\n]*\) \{[\s\S]*?^  \}/m);
if (!wrapper || !encoder) throw Error("Native notification encoder changed");
const ClientSession = vm.runInNewContext(
  `${wrapper[0]}\nclass Session {${encoder[0]}}; Session;`,
  {marshalEncode: codec.marshalEncode,
    toWireNotificationPayload: require(path.join(src, "network/attributeChangeWireValues.js")).toWireNotificationPayload});

const batch = compile("space/destiny/dispatch/batchDelivery.js", file => {
  if (file.endsWith("/utils/logger")) return log;
  if (file.endsWith("/network/clientSession")) return ClientSession;
  if (file.endsWith("/network/syncLedger")) return {isLedgerFileEnabled: () => false};
  if (file.endsWith("/network/spatialTrace")) return {isEnabled: () => false};
});
const history = compile("space/runtime/scene/destinyHistory.js", file => {
  if (file.endsWith("/utils/logger")) return log;
  if (file.endsWith("/dispatch/batchDelivery.js")) return batch;
  if (file.endsWith("/shipCloak")) return {isEntityCloaked: entity => entity.cloaked === true};
});
const visibility = compile("space/runtime/scene/visibility.js", file => {
  if (file.endsWith("/utils/logger")) return log;
  if (file.endsWith("/shipCloak")) return {isEntityCloaked: entity => entity.cloaked === true};
  if (file.endsWith("/destiny/index.js")) return actions;
  if (file.endsWith("/presentation/mode.js") || file.endsWith("/runtime/visibility") ||
      file.endsWith("/planet/planetOrbitalPlacement")) return {};
});
const statics = compile("space/runtime/scene/staticEntities.js", file => {
  if (file.endsWith("/sceneFeatureHooks")) return {notifyEntityRemoved() {}};
  if (file.endsWith("/common/numbers")) return undefined;
  return {};
});
const presentationSource = fs.readFileSync(path.join(src, "space/runtime/scene/presentation.js"), "utf8");
const removalMethods = ["queueTerminalDestructionEffect", "broadcastRemoveStaticEntity"].map(name => {
  const match = presentationSource.match(new RegExp(`^${name}\\([^\\n]*\\) \\{[\\s\\S]*?^  \\},`, "m"));
  if (!match) throw Error("Native terminal method changed: " + name);
  return match[0];
});
const terminal = vm.runInNewContext(`({${removalMethods.join("\n")}})`, {
  gridBubbles: grid, destiny: actions,
  toInt: require(path.join(src, "common/numbers.js")).toInt,
  getEntityMapKey: require(path.join(src, "space/destiny/identity/entityID.js")).getEntityMapKey,
});

function makeScene(entity = {kind: "asteroid", itemID: 5020593311760, radius: 1000, staticVisibilityScope: "bubble"}) {
  const park = grid.createGridBubbles();
  const near = {x: 0, y: 0, z: 0};
  const far = {x: grid.GRID_BUBBLE_BOX_METERS * 5, y: 0, z: 0};
  const received = [], refreshed = [];
  const scene = Object.assign({}, visibility, history, terminal, {removeStaticEntity: statics.removeStaticEntity}, {
    systemID: 30000142, sessions: new Map(), staticEntities: [entity], staticEntitiesByID: new Map([[entity.itemID, entity]]), dynamicEntities: new Map(),
    nextDestinyStamp: 500, destinyTickDriver: {lastTickSimTimeMs: 123}, evolving: false,
    getGridBubbles: () => park,
    removeBallFromGridBubbles: entity => grid.removeBall(park, entity.itemID),
    positionAuthority: {unregisterEntity() {}},
    isEvolving() {return this.evolving;},
    getEntityByID(id) {return this.staticEntitiesByID.get(id) || this.dynamicEntities.get(id) || null;},
    getShipEntityForSession(session) {return this.dynamicEntities.get(session.shipID);},
    sendStateRefresh(session) {refreshed.push(session.clientID); session._space.initialStateSent = false; return true;},
  });
  grid.reboxBall(park, entity.itemID, near);
  for (let id = 1; id <= 5; id++) {
    const ship = {kind: "ship", itemID: 900000 + id, position: id === 3 ? far : near};
    const session = {clientID: id, characterID: 100 + id, shipID: ship.itemID,
      _space: {initialStateSent: id !== 4}, socket: {destroyed: id === 5},
      sendNotification() {},
      sendEncodedNotification(name, idType, bytes, tuple) {
        if (this.failSend) throw Error("isolated recipient failure");
        received.push({id, name, idType, bytes, tuple});
      }};
    scene.sessions.set(id, session);
    scene.dynamicEntities.set(ship.itemID, ship);
    grid.reboxBall(park, ship.itemID, ship.position);
  }
  grid.additionsAndDeletions(park, {observers: scene.listGridBubbleObservers()});
  function tick(options = {}) {
    const frame = {stamp: scene.nextDestinyStamp};
    scene.applyDestinyTickList(frame);
    // Real memberships commit at the same native boundary. These tests do not
    // pretend to reproduce rendered AddBalls/RemoveBalls transition effects.
    if (options.transitions) scene.updateGridBubbles(frame);
    else grid.additionsAndDeletions(park, {observers: scene.listGridBubbleObservers()});
    scene.routeDestinyTickQueue(frame);
    const result = scene.sendDestinyBatches(frame);
    scene.nextDestinyStamp += 1;
    return result;
  }
  function move(id, position) {grid.reboxBall(park, scene.sessions.get(id).shipID, position);}
  return {scene, entity, park, received, refreshed, tick, move, near, far};
}

module.exports = {makeScene, grid, codec, actions, warnings};
