"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {createRuntime} = require("../lib/runtime");
const {normalizeConfig} = require("../lib/radius");
const config = normalizeConfig();
const ore = {yieldKind: "ore", originalQuantity: 8000, remainingQuantity: 1000, originalRadius: 1000};
const rock = () => ({kind: "asteroid", itemID: 5020593311760, radius: 1000});
const payload = (id, radius) => ["SetBallRadius", [id, radius]];

test("native tick API receives one radius action with no legacy dependency or immediate send", () => {
  const calls = [], entity = rock();
  const runtime = createRuntime({config, buildRadiusPayload: payload,
    buildSendOptions() {throw Error("legacy helper must not load");}});
  const scene = {queueBallHistory: (...args) => {calls.push(args); return 123;},
    sendDestinyUpdates() {throw Error("legacy sender must not run");}};
  runtime.present(entity, ore);
  runtime.publish(scene, entity, ore, 1000);
  assert.equal(entity.radius, 500);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], entity);
  assert.deepEqual(calls[0][1], [{payload: ["SetBallRadius", [5020593311760, 500]]}]);
  assert.equal(runtime.metrics.queued, 1);
  assert.equal(runtime.metrics.published, 0);
});

test("legacy delivery keeps ready/visible gates and isolates recipient failure", () => {
  const sent = [], warnings = [], entity = {...rock(), radius: 500};
  const runtime = createRuntime({config, buildRadiusPayload: payload,
    buildSendOptions: () => ({avoidCurrentHistoryInsertion: true}),
    isReady: session => session.ready, canReceive: (_scene, session) => session.visible,
    warn: error => warnings.push(error.message)});
  const sessions = [1, 2, 3, 4].map(id => ({id, ready: id !== 4, visible: id !== 3}));
  const scene = {sessions: new Map(sessions.map(s => [s.id, s])),
    getCurrentSessionDestinyStamp: s => 100 + s.id,
    sendDestinyUpdates(session, updates, wait, options) {
      if (session.id === 1) throw Error("recipient closed");
      sent.push({session, updates, options}); return 102;
    }};
  runtime.publish(scene, entity, ore, 1000);
  assert.deepEqual(sent.map(s => s.session.id), [2]);
  assert.equal(sent[0].updates[0].stamp, 102);
  assert.equal(sent[0].options.avoidCurrentHistoryInsertion, true);
  assert.deepEqual(warnings, ["recipient closed"]);
});

test("quiet baseline updates, terminal depletion, ice and gas do not publish radius", () => {
  const runtime = createRuntime({config, buildRadiusPayload: payload});
  const scene = {queueBallHistory() {throw Error("no radius action expected");}};
  const entity = {...rock(), radius: 500};
  for (const state of [{...ore, yieldKind: "ice"}, {...ore, yieldKind: "gas"}, {...ore, remainingQuantity: 0}]) {
    runtime.publish(scene, entity, state, 1000);
  }
  runtime.publish(scene, entity, ore, 1000, {broadcast: false});
  runtime.publish(scene, entity, ore, 500);
  assert.equal(runtime.metrics.resized, 0);
});

test("queue failures warn without changing mining state or invoking legacy delivery", () => {
  const warnings = [], entity = {...rock(), radius: 500};
  const runtime = createRuntime({config, buildRadiusPayload: payload, warn: error => warnings.push(error.message)});
  runtime.publish({queueBallHistory() {throw Error("queue unavailable");}}, entity, ore, 1000);
  assert.equal(entity.radius, 500);
  assert.deepEqual(warnings, ["queue unavailable"]);
  assert.equal(runtime.metrics.queued, 0);
});
