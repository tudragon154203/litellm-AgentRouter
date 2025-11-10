import { OpenAI } from "openai";

export function createDefaultClientFactory() {
  return (options) => {
    return new OpenAI({
      apiKey: options.apiKey,
      baseURL: options.baseURL,
      timeout: options.timeoutMs,
      defaultHeaders: {
        "User-Agent": options.userAgent,
      },
    });
  };
}
