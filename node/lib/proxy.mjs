import { NodeProxyConfig } from "./config.mjs";
import { NodeProxyServer } from "./server.mjs";
import { createDefaultClientFactory } from "./client.mjs";
import { logEvent } from "./logger.mjs";

export function createNodeUpstreamProxy({
  logger = console,
  openaiClientFactory,
  ...overrides
} = {}) {
  const config = NodeProxyConfig.fromEnv(overrides);
  const clientFactory = openaiClientFactory ?? createDefaultClientFactory();
  const proxy = new NodeProxyServer({ config, logger, openaiClientFactory: clientFactory });

  return {
    start: async () => {
      const address = await proxy.start();
      logEvent(logger, {
        event: "startup",
        port: config.port,
        upstream_base: config.upstreamBase,
        timeout_ms: config.timeoutMs,
      });
      return address;
    },
    stop: () => proxy.stop(),
    address: () => proxy.address(),
    config,
    logger,
  };
}
