import { fileURLToPath } from "node:url";
import { createNodeUpstreamProxy } from "./lib/server/proxy.mjs";

export { createNodeUpstreamProxy } from "./lib/server/proxy.mjs";
export { createRequestHandler } from "./lib/router/router.mjs";
export { DEFAULT_TIMEOUT_SECONDS } from "./lib/config/constants.mjs";

async function main() {
  const proxy = createNodeUpstreamProxy();
  await proxy.start();

  let shuttingDown = false;
  const shutdown = async () => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    
    try {
      await proxy.stop();
      process.exit(0);
    } catch (error) {
      console.error(JSON.stringify({ node_proxy: { event: "error", error: error.message } }));
      process.exit(1);
    }
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

const entrypoint = fileURLToPath(import.meta.url);
if (process.argv[1] === entrypoint) {
  main().catch((error) => {
    console.error(JSON.stringify({ node_proxy: { event: "error", error: error.message } }));
    process.exit(1);
  });
}
