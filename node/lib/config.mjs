import {
  DEFAULT_PORT,
  DEFAULT_HOST,
  DEFAULT_TIMEOUT_MS,
  DEFAULT_UPSTREAM_BASE,
} from "./constants.mjs";
import { DEFAULT_USER_AGENT } from "./fetchVersion.mjs";

export class NodeProxyConfig {
  constructor({ port, host, timeoutMs, upstreamBase, apiKey, userAgent }) {
    this.port = port;
    this.host = host;
    this.timeoutMs = timeoutMs;
    this.upstreamBase = upstreamBase;
    this.apiKey = apiKey;
    this.userAgent = userAgent;
  }

  static fromEnv(overrides = {}) {
    const port = overrides.port ?? DEFAULT_PORT;
    const host = overrides.host ?? DEFAULT_HOST;
    const timeoutMs = overrides.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    const upstreamBase = overrides.upstreamBase ?? process.env.OPENAI_BASE_URL ?? DEFAULT_UPSTREAM_BASE;
    const apiKey = overrides.apiKey ?? process.env.OPENAI_API_KEY;
    const userAgent = overrides.userAgent ?? process.env.NODE_USER_AGENT ?? DEFAULT_USER_AGENT;

    if (!apiKey) {
      throw new Error("OPENAI_API_KEY must be set for the Node upstream proxy");
    }

    return new NodeProxyConfig({
      port,
      host,
      timeoutMs,
      upstreamBase,
      apiKey,
      userAgent,
    });
  }
}
