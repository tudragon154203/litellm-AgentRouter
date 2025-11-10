import http from "node:http";
import os from "node:os";
import { OpenAI } from "openai";
import { fileURLToPath } from "node:url";

const DEFAULT_PORT = 4000;
const DEFAULT_HOST = "0.0.0.0";  // Listen on all interfaces for docker-compose compatibility
const DEFAULT_TIMEOUT_MS = 60_000;
const DEFAULT_UPSTREAM_BASE = "https://agentrouter.org/v1";
const DEFAULT_USER_AGENT = `QwenCode/0.2.0 (${os.platform().toLowerCase()}; ${os.arch()})`;

function getEnvNumber(key, fallback) {
  const value = process.env[key];
  if (value === undefined) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function logEvent(logger, payload) {
  try {
    logger.log(JSON.stringify({ node_proxy: payload }));
  } catch (error) {
    logger.error("Failed to log node_proxy event", error);
  }
}

class NodeProxyConfig {
  constructor({ port, host, timeoutMs, upstreamBase, apiKey, userAgent }) {
    this.port = port;
    this.host = host;
    this.timeoutMs = timeoutMs;
    this.upstreamBase = upstreamBase;
    this.apiKey = apiKey;
    this.userAgent = userAgent;
  }

  static fromEnv(overrides = {}) {
    const resolvedPort = overrides.port ?? DEFAULT_PORT;
    const resolvedHost = overrides.host ?? DEFAULT_HOST;
    const resolvedTimeout = overrides.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    const resolvedBase = overrides.upstreamBase ?? process.env.OPENAI_BASE_URL ?? DEFAULT_UPSTREAM_BASE;
    const resolvedApiKey = overrides.apiKey ?? process.env.OPENAI_API_KEY;
    const resolvedUserAgent =
      overrides.userAgent ??
      process.env.NODE_USER_AGENT ??
      DEFAULT_USER_AGENT;

    if (!resolvedApiKey) {
      throw new Error("OPENAI_API_KEY must be set for the Node upstream proxy");
    }

    return new NodeProxyConfig({
      port: resolvedPort,
      host: resolvedHost,
      timeoutMs: resolvedTimeout,
      upstreamBase: resolvedBase,
      apiKey: resolvedApiKey,
      userAgent: resolvedUserAgent,
    });
  }
}

function buildForwardHeaders(originalHeaders) {
  const forwarded = {};
  const requestId = originalHeaders["x-request-id"];
  if (requestId) {
    forwarded["X-Request-ID"] = requestId;
  }
  const userAgent = originalHeaders["user-agent"];
  if (userAgent) {
    forwarded["User-Agent"] = userAgent;
  }
  return forwarded;
}

function headersToPlainObject(headers) {
  const result = {};
  if (headers && typeof headers.forEach === "function") {
    headers.forEach((value, key) => {
      result[key.toLowerCase()] = value;
    });
  } else if (headers && typeof headers === "object") {
    Object.entries(headers).forEach(([key, value]) => {
      result[key.toLowerCase()] = value;
    });
  }
  return result;
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }

  if (!chunks.length) {
    return {};
  }

  const payload = Buffer.concat(chunks).toString("utf-8");
  return JSON.parse(payload);
}

function createRouteHandlers(client) {
  const chatHandler = client.chat?.completions?.create?.bind(client.chat.completions);
  const completionsHandler = client.completions?.create?.bind(client.completions);

  const wrap = (handler) => async (body, forwardedHeaders) => {
    if (!handler) {
      throw new Error("Handler not available");
    }

    const upstreamPromise = handler(body, { headers: forwardedHeaders });
    if (typeof upstreamPromise?.withResponse === "function") {
      return upstreamPromise.withResponse();
    }

    const data = await upstreamPromise;
    return {
      data,
      response: {
        status: 200,
        headers: new Headers(),
      },
    };
  };

  return {
    "/v1/chat/completions": wrap(chatHandler),
    "/v1/completions": wrap(completionsHandler),
  };
}

class NodeRequestRouter {
  constructor({ client, logger }) {
    this.logger = logger;
    this.handlers = createRouteHandlers(client);
  }

  async handle(req, res) {
    const method = (req.method ?? "GET").toUpperCase();
    const url = req.url ? new URL(req.url, `http://${req.headers.host ?? "localhost"}`) : new URL("/", "http://localhost");
    const requestId = req.headers["x-request-id"] ?? null;
    const startTime = Date.now();

    logEvent(this.logger, {
      event: "request_received",
      method,
      path: url.pathname,
      request_id: requestId,
    });

    if (method !== "POST") {
      res.writeHead(405, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Method not allowed" }));
      logEvent(this.logger, {
        event: "request_failed",
        status: 405,
        error: "Method not allowed",
        request_id: requestId,
      });
      return;
    }

    const handler = this.handlers[url.pathname];
    if (!handler) {
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Not found" }));
      logEvent(this.logger, {
        event: "request_failed",
        status: 404,
        error: "Not found",
        request_id: requestId,
      });
      return;
    }

    let payload;
    try {
      payload = await readJsonBody(req);
    } catch (error) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Invalid JSON payload", detail: error.message }));
      logEvent(this.logger, {
        event: "request_failed",
        status: 400,
        error: "Invalid JSON payload",
        request_id: requestId,
      });
      return;
    }

    const forwardedHeaders = buildForwardHeaders(req.headers);

    try {
      const { data, response } = await handler(payload, forwardedHeaders);
      const normalizedHeaders = headersToPlainObject(response.headers);
      const status = response.status ?? 200;
      const responseHeaders = {
        ...normalizedHeaders,
        "content-type": normalizedHeaders["content-type"] ?? "application/json",
      };

      const downstreamRequestId = normalizedHeaders["x-request-id"] ?? forwardedHeaders["X-Request-ID"];
      if (downstreamRequestId) {
        responseHeaders["x-request-id"] = downstreamRequestId;
      }

      res.writeHead(status, responseHeaders);
      res.end(JSON.stringify(data));

      logEvent(this.logger, {
        event: "request_completed",
        status,
        duration_ms: Date.now() - startTime,
        request_id: downstreamRequestId,
      });
    } catch (error) {
      const status = error?.status ?? 502;
      res.writeHead(status, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: error?.message ?? "upstream_error" }));
      logEvent(this.logger, {
        event: "request_failed",
        status,
        error: error?.message ?? "upstream_error",
        request_id: requestId,
      });
    }
  }
}

function createRequestHandler({ client, logger }) {
  const router = new NodeRequestRouter({ client, logger });
  return router.handle.bind(router);
}

export { createRequestHandler, DEFAULT_TIMEOUT_MS };

class NodeProxyServer {
  constructor({ config, logger, openaiClientFactory }) {
    this.config = config;
    this.logger = logger;
    this.client = openaiClientFactory({
      apiKey: config.apiKey,
      baseURL: config.upstreamBase,
      timeoutMs: config.timeoutMs,
      userAgent: config.userAgent,
    });
    this.server = http.createServer(createRequestHandler({ client: this.client, logger }));
  }

  start() {
    return new Promise((resolve, reject) => {
      const onError = (error) => {
        this.server.off("listening", onListen);
        reject(error);
      };

      const onListen = () => {
        this.server.off("error", onError);
        logEvent(this.logger, {
          event: "ready",
          port: this.server.address()?.port ?? this.config.port,
          upstream_base: this.config.upstreamBase,
        });
        resolve(this.server.address());
      };

      this.server.once("error", onError);
      this.server.once("listening", onListen);
      this.server.listen(this.config.port, this.config.host);
    });
  }

  stop() {
    return new Promise((resolve, reject) => {
      if (!this.server.listening) {
        resolve();
        return;
      }

      this.server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        logEvent(this.logger, { event: "shutdown" });
        resolve();
      });
    });
  }

  address() {
    return this.server.address();
  }
}

function createDefaultClientFactory(logger) {
  return (options) => {
    const defaultHeaders = { "User-Agent": options.userAgent };
    return new OpenAI({
      apiKey: options.apiKey,
      baseURL: options.baseURL,
      timeout: options.timeoutMs,
      defaultHeaders,
    });
  };
}

export function createNodeUpstreamProxy({
  logger = console,
  openaiClientFactory,
  ...overrides
} = {}) {
  const config = NodeProxyConfig.fromEnv(overrides);
  const clientFactory = openaiClientFactory ?? createDefaultClientFactory(logger);
  const proxy = new NodeProxyServer({ config, logger, openaiClientFactory: clientFactory });

  const start = async () => {
    const address = await proxy.start();
    logEvent(logger, {
      event: "startup",
      port: config.port,
      upstream_base: config.upstreamBase,
      timeout_ms: config.timeoutMs,
    });
    return address;
  };

  const stop = () => proxy.stop();

  return {
    start,
    stop,
    address: () => proxy.address(),
    config,
    logger,
  };
}

async function main() {
  const proxy = createNodeUpstreamProxy();

  await proxy.start();
  let shuttingDown = false;

  const shutdown = async () => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    await proxy.stop();
    process.exit(0);
  };

  const handleSignal = () => {
    shutdown().catch((error) => {
      console.error(JSON.stringify({ node_proxy: { event: "error", error: error.message } }));
      process.exit(1);
    });
  };

  process.on("SIGINT", handleSignal);
  process.on("SIGTERM", handleSignal);
}

const entrypoint = fileURLToPath(import.meta.url);
if (process.argv[1] === entrypoint) {
  main().catch((error) => {
    console.error(JSON.stringify({ node_proxy: { event: "error", error: error.message } }));
    process.exit(1);
  });
}
