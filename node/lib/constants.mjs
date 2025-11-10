import os from "node:os";

export const DEFAULT_PORT = 4000;
export const DEFAULT_HOST = "0.0.0.0";
export const DEFAULT_TIMEOUT_MS = 60_000;
export const DEFAULT_UPSTREAM_BASE = "https://agentrouter.org/v1";
export const DEFAULT_USER_AGENT = `QwenCode/0.2.0 (${os.platform().toLowerCase()}; ${os.arch()})`;
