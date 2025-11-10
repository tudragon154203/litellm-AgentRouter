import assert from "node:assert";
import { test } from "node:test";
import { logEvent } from "../../lib/logger.mjs";

test("logEvent logs structured JSON", () => {
  const logs = [];
  const mockLogger = {
    log: (msg) => logs.push(msg),
    error: () => {},
  };

  logEvent(mockLogger, { event: "test", data: "value" });

  assert.strictEqual(logs.length, 1);
  const parsed = JSON.parse(logs[0]);
  assert.deepStrictEqual(parsed, {
    node_proxy: { event: "test", data: "value" },
  });
});

test("logEvent handles logging errors gracefully", () => {
  const errors = [];
  const mockLogger = {
    log: () => {
      throw new Error("logging failed");
    },
    error: (msg, err) => errors.push({ msg, err }),
  };

  logEvent(mockLogger, { event: "test" });

  assert.strictEqual(errors.length, 1);
  assert.strictEqual(errors[0].msg, "Failed to log node_proxy event");
});

test("logEvent handles circular references", () => {
  const errors = [];
  const mockLogger = {
    log: () => {
      throw new Error("circular");
    },
    error: (msg) => errors.push(msg),
  };

  const circular = { a: 1 };
  circular.self = circular;

  logEvent(mockLogger, circular);

  assert.strictEqual(errors.length, 1);
});
