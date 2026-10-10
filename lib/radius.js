"use strict";

const DEFAULTS = Object.freeze({
  radiusExponent: 1 / 3,
  minimumRadiusRatio: 0.005,
  minimumRadiusMeters: 2,
  resizeDurationMs: 600,
  depletionDurationMs: 650,
  dustEnabled: true,
  dustIntensity: 1,
  dustLifetimeMs: 1400,
  dustMaxConcurrent: 24,
});

function normalizeConfig(input = {}) {
  const bounds = {
    radiusExponent: [0.1, 1], minimumRadiusRatio: [0.0001, 0.1],
    minimumRadiusMeters: [1.01, 100], resizeDurationMs: [0, 3000],
    depletionDurationMs: [0, 2000],
    dustIntensity: [0, 3], dustLifetimeMs: [300, 4000], dustMaxConcurrent: [1, 64],
  };
  const result = {};
  for (const [key, [minimum, maximum]] of Object.entries(bounds)) {
    const value = input[key] === undefined ? DEFAULTS[key] : input[key];
    if (typeof value !== "number" || !Number.isFinite(value) || value < minimum || value > maximum) {
      throw new Error(`Invalid ${key}: expected a number from ${minimum} to ${maximum}`);
    }
    result[key] = value;
  }
  if (!Number.isInteger(result.dustMaxConcurrent)) throw new Error("dustMaxConcurrent must be an integer");
  result.dustEnabled = input.dustEnabled === undefined ? DEFAULTS.dustEnabled : input.dustEnabled;
  if (typeof result.dustEnabled !== "boolean") throw new Error("dustEnabled must be true or false");
  return Object.freeze(result);
}

function isOreAsteroid(entity, state) {
  return String(entity?.kind || "").toLowerCase() === "asteroid" &&
    String(state?.yieldKind || "").toLowerCase() === "ore";
}

function radiusForState(state, config = DEFAULTS) {
  const originalRadius = Number(state?.originalRadius);
  const originalQuantity = Number(state?.originalQuantity);
  const remainingQuantity = Number(state?.remainingQuantity);
  if (![originalRadius, originalQuantity, remainingQuantity].every(Number.isFinite) ||
      originalRadius <= 0 || originalQuantity <= 0 || remainingQuantity < 0) return null;
  const fraction = Math.min(1, remainingQuantity / originalQuantity);
  const minimum = Math.min(originalRadius,
    Math.max(config.minimumRadiusMeters, originalRadius * config.minimumRadiusRatio));
  return Math.max(minimum, originalRadius * Math.pow(fraction, config.radiusExponent));
}

module.exports = { DEFAULTS, normalizeConfig, isOreAsteroid, radiusForState };
