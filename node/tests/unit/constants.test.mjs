import assert from "node:assert";
import { test } from "node:test";
import {
  DEFAULT_PORT,
  DEFAULT_HOST,
  DEFAULT_TIMEOUT_MS,
  DEFAULT_UPSTREAM_BASE,
} from "../../lib/constants.mjs";
import { DEFAULT_USER_AGENT } from "../../lib/fetchVersion.mjs";

test("DEFAULT_PORT is 4000", () => {
  assert.strictEqual(DEFAULT_PORT, 4000);
});

test("DEFAULT_HOST is 0.0.0.0", () => {
  assert.strictEqual(DEFAULT_HOST, "0.0.0.0");
});

test("DEFAULT_TIMEOUT_MS is 60000", () => {
  assert.strictEqual(DEFAULT_TIMEOUT_MS, 60_000);
});

test("DEFAULT_UPSTREAM_BASE is agentrouter.org", () => {
  assert.strictEqual(DEFAULT_UPSTREAM_BASE, "https://agentrouter.org/v1");
});

test("DEFAULT_USER_AGENT includes QwenCode", () => {
  assert.ok(DEFAULT_USER_AGENT.includes("QwenCode"));
  assert.ok(DEFAULT_USER_AGENT.includes("0.2.0"));
});
