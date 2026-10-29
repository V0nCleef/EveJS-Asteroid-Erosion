"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
if (!process.env.EVEJS_TEST_ROOT) {
  test("native 261028.1 replay requires an isolated EVEJS_TEST_ROOT", {skip: true}, () => {});
} else {
const {makeScene, grid, codec, actions} = require("./native-tick-fixture.cjs");
const {createRuntime} = require("../lib/runtime.js");
const {normalizeConfig} = require("../lib/radius.js");
const config = normalizeConfig();
const ore = {yieldKind: "ore", originalQuantity: 8000, remainingQuantity: 1000, originalRadius: 1000};
function runtime(warnings = []) {
  return createRuntime({config, buildRadiusPayload: actions.buildSetBallRadiusPayload,
    buildSendOptions: () => {throw Error("legacy delivery must not run");},
    isReady: () => {throw Error("legacy readiness must not run");},
    canReceive: () => {throw Error("legacy visibility must not run");},
    warn: error => warnings.push(error.message)});
}
function publish(fixture, instance = runtime()) {
  instance.present(fixture.entity, ore);
  instance.publish(fixture.scene, fixture.entity, ore, 1000);
  return instance;
}

test("0.2.1 control silently drops intermediate radius on the new scene API", () => {
  const old = require("./fixtures/runtime-0.2.1.cjs").createRuntime;
  const fixture = makeScene();
  publish(fixture, old({config, buildRadiusPayload: actions.buildSetBallRadiusPayload}));
  assert.equal(fixture.entity.radius, 500);
  assert.equal(fixture.scene._destinyHistory, undefined);
  assert.equal(fixture.tick().sends, 0);
});

test("one native Ball history entry reaches ready visible miner and observer through real wire encoding", () => {
  const fixture = makeScene();
  const instance = publish(fixture);
  assert.equal(instance.metrics.queued, 1);
  assert.equal(fixture.received.length, 0, "no direct send before native tick");
  assert.equal(fixture.scene.getDestinyHistory().list.length, 1);
  const result = fixture.tick();
  assert.equal(result.encodes, 1, "bubble payload encoded once");
  assert.equal(result.sends, 2);
  assert.deepEqual(fixture.received.map(item => item.id), [1, 2]);
  assert.equal(fixture.received[0].bytes, fixture.received[1].bytes);
  for (const item of fixture.received) {
    assert.equal(item.name, "DoDestinyUpdate");
    assert.equal(item.idType, "clientID");
    const tuple = codec.marshalDecodeExact(item.bytes)[1][1];
    assert.equal(tuple.length, 2);
    assert.equal(tuple[1], false);
    const [stamp, payload] = tuple[0].items[0];
    assert.equal(stamp, 500);
    assert.equal(codec.strVal(payload[0]), "SetBallRadius");
    assert.equal(payload[1][0], 5020593311760n);
    assert.equal(payload[1][1], 500);
  }
});

test("routing uses post-update memberships rather than stale recipients at mining time", () => {
  const fixture = makeScene();
  publish(fixture);
  fixture.move(2, fixture.far);
  fixture.move(3, fixture.near);
  fixture.tick();
  assert.deepEqual(fixture.received.map(item => item.id), [1, 3]);
});

test("a recipient disconnected before flush is omitted; a failed send preserves the other client and native recovery", () => {
  const disconnected = makeScene();
  publish(disconnected);
  disconnected.scene.sessions.get(2).socket.destroyed = true;
  disconnected.tick();
  assert.deepEqual(disconnected.received.map(item => item.id), [1]);
  const fixture = makeScene();
  publish(fixture);
  fixture.scene.sessions.get(1).failSend = true;
  const result = fixture.tick();
  assert.equal(result.sends, 1);
  assert.deepEqual(fixture.received.map(item => item.id), [2]);
  assert.deepEqual(fixture.refreshed, [1]);
  assert.equal(fixture.scene.sessions.get(1)._space.initialStateSent, false);
});

test("a rock removed before routing drops pending radius without a stale update after depletion", () => {
  const fixture = makeScene();
  publish(fixture);
  fixture.scene.staticEntitiesByID.delete(fixture.entity.itemID);
  grid.removeBall(fixture.park, fixture.entity.itemID);
  fixture.tick();
  assert.equal(fixture.received.length, 0);
});

test("native static depletion delivers its terminal effect and packaged removal on the same tick to both observers", () => {
  const fixture = makeScene();
  publish(fixture);
  assert.equal(fixture.scene.removeStaticEntity(fixture.entity.itemID, {terminalDestructionEffectID: 2}).success, true);
  assert.equal(fixture.scene.getEntityByID(fixture.entity.itemID), null);
  fixture.tick({transitions: true});
  for (const id of [1, 2]) {
    const items = fixture.received.filter(item => item.id === id);
    assert.equal(items.length, 2, "native character removal and bubble effect batches");
    assert.equal(items[0].tuple[1], true, "character removal waits for its bubble effect");
    const state = items.flatMap(item => item.tuple[0].items);
    assert.equal(state.some(([, payload]) => payload[0] === "SetBallRadius"), false);
    const effect = state.find(([, payload]) => payload[0] === "TerminalPlayDestructionEffect");
    assert.equal(effect[0], 500);
    assert.deepEqual(Array.from(effect[1][1]), [5020593311760, 2]);
    const packaged = state.find(([, payload]) => payload[0] === "PackagedAction");
    assert.equal(packaged[0], effect[0]);
    assert.ok(packaged);
  }
  assert.equal(fixture.received.some(item => item.id >= 3), false);
});

test("silent/baseline updates, unchanged radii, ice, gas and terminal depletion never queue extra radius", () => {
  const fixture = makeScene();
  const instance = runtime();
  for (const state of [{...ore, yieldKind: "ice"}, {...ore, yieldKind: "gas"}, {...ore, remainingQuantity: 0}]) {
    instance.publish(fixture.scene, {...fixture.entity, radius: 500}, state, 1000);
  }
  instance.publish(fixture.scene, {...fixture.entity, radius: 500}, ore, 1000, {broadcast: false});
  instance.publish(fixture.scene, {...fixture.entity, radius: 500}, ore, 500);
  assert.equal(fixture.scene._destinyHistory, undefined);
  const warnings = [], failed = runtime(warnings);
  failed.publish({queueBallHistory() {throw Error("isolated queue failure");}}, {...fixture.entity, radius: 500}, ore, 1000);
  assert.deepEqual(warnings, ["isolated queue failure"]);
});

test("loader adapter executes the new delivery path without resolving deleted sendOptions", () => {
  const Module = require("node:module");
  const {KEY} = require("../lib/source.js");
  const saved = Module.prototype._compile;
  const fixture = makeScene();
  try {
    const state = require("../loader.js").install(process.env.EVEJS_TEST_ROOT);
    publish(fixture, state.runtime);
    assert.equal(state.active, true);
    assert.equal(fixture.tick().sends, 2);
  } finally {
    Module.prototype._compile = saved;
    delete globalThis[Symbol.for(KEY)];
  }
});

}
