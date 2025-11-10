import assert from "node:assert";
import { test } from "node:test";

import { createNodeUpstreamProxy, createRequestHandler, DEFAULT_TIMEOUT_MS } from "../upstream-proxy.mjs";

const SILENT_LOGGER = { log: () => {}, error: () => {} };

function createFakeUpstreamPayload({
  data = { forwarded: true },
  status = 200,
  requestId = "test-request",
} = {}) {
  const headers = new Headers();
  headers.set("content-type", "application/json");
  headers.set("x-request-id", requestId);

  return {
    data,
    response: {
      status,
      headers,
    },
  };
}

function createMockRequest({
  path = "/v1/chat/completions",
  body,
  headers = {},
  method = "POST",
} = {}) {
  const payloadBuffer = body ? Buffer.from(JSON.stringify(body)) : null;
  let consumed = false;

  return {
    method,
    url: path,
    headers: {
      host: "127.0.0.1",
      ...headers,
    },
    async *[Symbol.asyncIterator]() {
      if (consumed) {
        return;
      }
      consumed = true;
      if (payloadBuffer) {
        yield payloadBuffer;
      }
    },
  };
}

class MockResponse {
  constructor() {
    this.statusCode = 200;
    this.headers = {};
    this.body = "";
  }

  writeHead(status, headers) {
    this.statusCode = status;
    this.headers = { ...headers };
  }

  end(payload) {
    this.body = payload?.toString("utf-8") ?? "";
  }
}

test("forwards chat completions requests through OpenAI client", async () => {
  const requests = [];
  const fakePayload = createFakeUpstreamPayload({
    data: { ok: true },
    requestId: "chat-123",
  });

  const fakeClient = {
    chat: {
      completions: {
        create(body, options) {
          requests.push({ body, options });
          return {
            withResponse: async () => fakePayload,
          };
        },
      },
    },
    completions: {
      create() {
        throw new Error("completions endpoint should not be called");
      },
    },
  };

  const handler = createRequestHandler({
    client: fakeClient,
    logger: SILENT_LOGGER,
  });

  const req = createMockRequest({
    path: "/v1/chat/completions",
    body: { model: "gpt-5" },
    headers: {
      "x-request-id": "chat-req",
      "user-agent": "node-test-agent",
    },
  });

  const res = new MockResponse();
  await handler(req, res);

  assert.strictEqual(res.statusCode, 200);
  assert.deepStrictEqual(JSON.parse(res.body), fakePayload.data);
  assert.strictEqual(requests.length, 1);
  assert.strictEqual(requests[0].options.headers["User-Agent"], "node-test-agent");
  assert.strictEqual(requests[0].options.headers["X-Request-ID"], "chat-req");
});

test("routes completions requests without hitting chat handler", async () => {
  const requests = [];
  const fakePayload = createFakeUpstreamPayload({ data: { ok: "completions" } });

  const fakeClient = {
    chat: {
      completions: {
        create() {
          throw new Error("chat endpoint should not be called");
        },
      },
    },
    completions: {
      create(body, options) {
        requests.push({ body, options });
        return {
          withResponse: async () => fakePayload,
        };
      },
    },
  };

  const handler = createRequestHandler({
    client: fakeClient,
    logger: SILENT_LOGGER,
  });

  const req = createMockRequest({
    path: "/v1/completions",
    body: { prompt: "Hello" },
  });

  const res = new MockResponse();
  await handler(req, res);

  assert.strictEqual(res.statusCode, 200);
  assert.deepStrictEqual(JSON.parse(res.body), fakePayload.data);
  assert.strictEqual(requests.length, 1);
});

test("propagates upstream errors and status codes", async () => {
  const fakeError = new Error("upstream failure");
  fakeError.status = 418;

  const fakeClient = {
    chat: {
      completions: {
        create() {
          return {
            withResponse: async () => {
              throw fakeError;
            },
          };
        },
      },
    },
    completions: {
      create() {
        throw new Error("should not call completions");
      },
    },
  };

  const handler = createRequestHandler({
    client: fakeClient,
    logger: SILENT_LOGGER,
  });

  const req = createMockRequest({ path: "/v1/chat/completions" });
  const res = new MockResponse();
  await handler(req, res);

  assert.strictEqual(res.statusCode, 418);
  assert.strictEqual(JSON.parse(res.body).error, "upstream failure");
});

test("uses default port 4000 and hardcoded timeout", () => {
  const recordedOptions = [];

  const proxy = createNodeUpstreamProxy({
    host: "127.0.0.1",
    logger: SILENT_LOGGER,
    apiKey: "sk-test",
    openaiClientFactory: (options) => {
      recordedOptions.push(options);
      const fakePayload = createFakeUpstreamPayload();
      const withResponse = async () => fakePayload;
      const createHandler = () => ({ withResponse });
      return {
        chat: { completions: { create: createHandler } },
        completions: { create: createHandler },
      };
    },
  });

  assert.strictEqual(proxy.config.port, 4000);
  assert.strictEqual(proxy.config.timeoutMs, DEFAULT_TIMEOUT_MS);
  assert.strictEqual(recordedOptions[0].timeoutMs, DEFAULT_TIMEOUT_MS);
});
