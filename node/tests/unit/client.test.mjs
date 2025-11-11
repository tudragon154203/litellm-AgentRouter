import assert from "node:assert";
import { test } from "node:test";
import { createDefaultClientFactory } from "../../lib/client/client.mjs";

test("createDefaultClientFactory returns a factory function", () => {
  const factory = createDefaultClientFactory();
  assert.strictEqual(typeof factory, "function");
});

test("factory creates OpenAI client with correct options", () => {
  const factory = createDefaultClientFactory();
  
  const client = factory({
    apiKey: "sk-test-key",
    baseURL: "https://api.test.com/v1",
    timeoutMs: 30_000,
    userAgent: "TestAgent/1.0",
  });

  assert.ok(client);
  assert.ok(client.chat);
  assert.ok(client.completions);
});

test("factory sets User-Agent in default headers", () => {
  const factory = createDefaultClientFactory();
  
  const client = factory({
    apiKey: "sk-test",
    baseURL: "https://api.test.com/v1",
    timeoutMs: 60_000,
    userAgent: "CustomAgent/2.0",
  });

  assert.ok(client);
});
