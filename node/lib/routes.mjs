export function createRouteHandlers(client) {
  const wrapHandler = (handler) => async (body, forwardedHeaders) => {
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
    "/v1/chat/completions": wrapHandler(client.chat?.completions?.create?.bind(client.chat.completions)),
    "/v1/completions": wrapHandler(client.completions?.create?.bind(client.completions)),
  };
}
