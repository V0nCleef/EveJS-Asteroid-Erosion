"use strict";

const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");
const { KEY, digest } = require("./source");
const HANDSHAKE_BASELINE = "4fc3c37ec83c443c1497a3daba57d7157d05bbe55af3be2d5545b6162398ebc9";

function supportsHandshake(source) {
  return digest(String(source).replace(/\r\n/g, "\n")) === HANDSHAKE_BASELINE;
}

function createDelivery(modRoot, config) {
  const source = "# coding: utf-8\n_ae_config = __import__('json').loads(" + JSON.stringify(JSON.stringify(config)) + ")\n" +
    fs.readFileSync(path.join(modRoot, "client/companion.py"), "utf8");
  const encoded = zlib.deflateSync(Buffer.from(source, "utf8"), { level: 9 }).toString("base64");
  if (encoded.length > 64 * 1024) throw new Error("Asteroid companion exceeds its payload bound");
  const execute = `try:\n eval(compile(__import__('zlib').decompress(__import__('base64').b64decode('${encoded}')), '<asteroid-erosion>', 'exec'), {'__builtins__': __builtins__, '_ae_context': _ae_context})\nexcept Exception:\n print('ASTEROID_EROSION:CLIENT_FAILED')\n`;
  const expression = `eval(compile(${JSON.stringify(execute)}, '<asteroid-erosion-delivery>', 'exec'), {'__builtins__': __builtins__, '_ae_context': globals()})`;
  return {
    compose(original) {
      if (!Buffer.isBuffer(original) || original.length < 5 || original[0] !== 0x74 || original.readUInt32LE(1) !== original.length - 5) {
        throw new Error("Unsupported login expression envelope");
      }
      const previous = original.subarray(5).toString("latin1");
      const bytes = Buffer.from(`(lambda _ae_result: (${expression}, _ae_result)[1])(${previous})`, "latin1");
      if (bytes.length > 1024 * 1024) throw new Error("Combined login expression exceeds one MiB");
      const header = Buffer.alloc(5);
      header[0] = 0x74;
      header.writeUInt32LE(bytes.length, 1);
      return Buffer.concat([header, bytes]);
    },
  };
}

function installHandshake(Service, { codec, delivery, active = () => true }) {
  const installed = Symbol.for(KEY + ".handshake");
  const delivered = Symbol.for(KEY + ".delivered");
  if (Service.prototype[installed]) return;
  if (typeof Service.prototype._sendPacket !== "function") throw new Error("Login send hook changed");
  const previous = Service.prototype._sendPacket;
  // Compose at packet send time so AutoMining's exact-source login hook and
  // other outgoing-packet companions can coexist in either preload order.
  Service.prototype._sendPacket = function(packet) {
    if (active() && !this[delivered] && Number(this.userId) > 0 && Buffer.isBuffer(packet) &&
        packet.length >= 5 && packet.length <= 1024 * 1024 && packet.readUInt32LE(0) === packet.length - 4) {
      try {
        const value = codec.marshalDecodeExact(packet.subarray(4));
        if (Array.isArray(value) && value.length === 4 && codec.strVal(value[0]) === "" &&
            Array.isArray(value[1]) && value[1].length === 2 && Buffer.isBuffer(value[1][0]) && value[1][1] === false &&
            value[2]?.type === "dict" && codec.strVal(codec.dictGet(value[3], "challenge_responsehash")) === "55087") {
          const before = codec.marshalEncode(value[1][0]), after = codec.marshalEncode(delivery.compose(value[1][0]));
          if (before[0] !== codec.MARSHAL_HEADER || after[0] !== codec.MARSHAL_HEADER) throw new Error("Native codec header changed");
          const oldValue = before.subarray(5), newValue = after.subarray(5), at = packet.indexOf(oldValue, 9);
          if (at < 0 || packet.indexOf(oldValue, at + oldValue.length) >= 0) throw new Error("Login function is not uniquely encoded");
          packet = codec.wrapPacket(Buffer.concat([packet.subarray(4, at), newValue, packet.subarray(at + oldValue.length)]));
          this[delivered] = true;
        }
      } catch (error) {
        console.error("[Asteroid Erosion] Client delivery failed; original login preserved: " + error.message);
      }
    }
    return previous.call(this, packet);
  };
  Object.defineProperty(Service.prototype, installed, { value: true });
}

module.exports = { HANDSHAKE_BASELINE, supportsHandshake, createDelivery, installHandshake };
