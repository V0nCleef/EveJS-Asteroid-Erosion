"use strict";

const { isOreAsteroid, radiusForState } = require("../../lib/radius");

function createRuntime({ config, active = () => true, buildRadiusPayload, buildSendOptions, canReceive, isReady, warn = () => {} }) {
  const metrics = { resized: 0, published: 0 };
  return {
    metrics,
    present(entity, state) {
      if (!active() || !isOreAsteroid(entity, state)) return;
      const radius = radiusForState(state, config);
      if (radius !== null && state.remainingQuantity > 0) entity.radius = radius;
    },
    publish(scene, entity, state, previousRadius, options = {}) {
      if (!active() || !isOreAsteroid(entity, state) || state.remainingQuantity <= 0 || options.broadcast === false) return;
      if (!Number.isFinite(entity.radius) || Math.abs(entity.radius - previousRadius) < 0.000001) return;
      if (!(scene?.sessions instanceof Map) || typeof scene.sendDestinyUpdates !== "function") return;
      metrics.resized += 1;
      // Static balls need explicit materialization checks: the native movement
      // broadcast treats unknown/non-dynamic balls as globally deliverable.
      for (const session of scene.sessions.values()) {
        if (!isReady(session) || !canReceive(scene, session, entity)) continue;
        try {
          const stamp = scene.getCurrentSessionDestinyStamp(session);
          const sent = scene.sendDestinyUpdates(session, [{
            stamp, payload: buildRadiusPayload(entity.itemID, entity.radius),
          }], false, buildSendOptions());
          if (sent !== false && sent !== null) metrics.published += 1;
        } catch (error) { warn(error); }
      }
    },
  };
}

module.exports = { createRuntime };
