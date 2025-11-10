import { logEvent } from "./logger.mjs";
import { buildForwardHeaders, headersToPlainObject, readJsonBody } from "./http-utils.mjs";
import { createRouteHandlers } from "./routes.mjs";

export class NodeRequestRouter {
  constructor({ client, logger }) {
    this.logger = logger;
    this.handlers = createRouteHandlers(client);
  }

  async handle(req, res) {
    const method = (req.method ?? "GET").toUpperCase();
    const url = this._parseUrl(req);
    const requestId = req.headers["x-request-id"] ?? null;
    const startTime = Date.now();

    this._logRequest(method, url.pathname, requestId);

    if (method !== "POST") {
      return this._sendError(res, 405, "Method not allowed", requestId);
    }

    const handler = this.handlers[url.pathname];
    if (!handler) {
      return this._sendError(res, 404, "Not found", requestId);
    }

    let payload;
    try {
      payload = await readJsonBody(req);
    } catch (error) {
      return this._sendError(res, 400, "Invalid JSON payload", requestId, error.message);
    }

    const forwardedHeaders = buildForwardHeaders(req.headers);

    try {
      const { data, response } = await handler(payload, forwardedHeaders);
      this._sendSuccess(res, data, response, forwardedHeaders, startTime);
    } catch (error) {
      const status = error?.status ?? 502;
      const message = error?.message ?? "upstream_error";
      this._sendError(res, status, message, requestId);
    }
  }

  _parseUrl(req) {
    const host = req.headers.host ?? "localhost";
    return req.url ? new URL(req.url, `http://${host}`) : new URL("/", "http://localhost");
  }

  _logRequest(method, path, requestId) {
    logEvent(this.logger, {
      event: "request_received",
      method,
      path,
      request_id: requestId,
    });
  }

  _sendError(res, status, error, requestId, detail = null) {
    const payload = { error };
    if (detail) {
      payload.detail = detail;
    }

    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify(payload));

    logEvent(this.logger, {
      event: "request_failed",
      status,
      error,
      request_id: requestId,
    });
  }

  _sendSuccess(res, data, response, forwardedHeaders, startTime) {
    const normalizedHeaders = headersToPlainObject(response.headers);
    const status = response.status ?? 200;
    const responseHeaders = {
      ...normalizedHeaders,
      "content-type": normalizedHeaders["content-type"] ?? "application/json",
    };

    const requestId = normalizedHeaders["x-request-id"] ?? forwardedHeaders["X-Request-ID"];
    if (requestId) {
      responseHeaders["x-request-id"] = requestId;
    }

    res.writeHead(status, responseHeaders);
    res.end(JSON.stringify(data));

    logEvent(this.logger, {
      event: "request_completed",
      status,
      duration_s: ((Date.now() - startTime) / 1000).toFixed(2),
      request_id: requestId,
    });
  }
}

export function createRequestHandler({ client, logger }) {
  const router = new NodeRequestRouter({ client, logger });
  return router.handle.bind(router);
}
