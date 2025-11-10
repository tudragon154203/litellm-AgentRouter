export function logEvent(logger, payload) {
  try {
    logger.log(JSON.stringify({ node_proxy: payload }));
  } catch (error) {
    logger.error("Failed to log node_proxy event", error);
  }
}
