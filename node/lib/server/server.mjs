import http from "node:http";
import { logEvent } from "../utils/logger.mjs";
import { createRequestHandler } from "../router/router.mjs";

export class NodeProxyServer {
  constructor({ config, logger, openaiClientFactory }) {
    this.config = config;
    this.logger = logger;
    this.client = this._createClient(openaiClientFactory);
    this.server = http.createServer(createRequestHandler({ client: this.client, logger }));
  }

  _createClient(factory) {
    return factory({
      apiKey: this.config.apiKey,
      baseURL: this.config.upstreamBase,
      timeoutMs: this.config.timeoutMs,
      userAgent: this.config.userAgent,
    });
  }

  start() {
    return new Promise((resolve, reject) => {
      const onError = (error) => {
        this.server.off("listening", onListen);
        reject(error);
      };

      const onListen = () => {
        this.server.off("error", onError);
        const address = this.server.address();
        logEvent(this.logger, {
          event: "ready",
          port: address?.port ?? this.config.port,
          upstream_base: this.config.upstreamBase,
        });
        resolve(address);
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
