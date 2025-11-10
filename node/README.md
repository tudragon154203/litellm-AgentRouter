# Node Upstream Proxy

Modular Node.js proxy for forwarding OpenAI-compatible requests to upstream providers.

## Structure

```
node/
├── upstream-proxy.mjs       # Entry point and CLI
├── lib/                     # Core modules
│   ├── config.mjs           # Configuration management
│   ├── constants.mjs        # Shared constants
│   ├── client.mjs           # OpenAI client factory
│   ├── proxy.mjs            # Public API factory
│   ├── server.mjs           # HTTP server lifecycle
│   ├── router.mjs           # Request routing and middleware
│   ├── routes.mjs           # Route handler definitions
│   ├── http-utils.mjs       # HTTP utilities
│   └── logger.mjs           # Structured logging
└── tests/
    ├── unit/                # Unit tests (isolated components)
    │   ├── client.test.mjs
    │   ├── config.test.mjs
    │   ├── constants.test.mjs
    │   ├── http-utils.test.mjs
    │   ├── logger.test.mjs
    │   ├── router.test.mjs
    │   └── routes.test.mjs
    └── integration/         # Integration tests (end-to-end)
        └── upstream-proxy.test.mjs
```

## Usage

```javascript
import { createNodeUpstreamProxy } from "./node/upstream-proxy.mjs";

const proxy = createNodeUpstreamProxy({
  port: 4000,
  upstreamBase: "https://api.openai.com/v1",
});

await proxy.start();
```

## Testing

```bash
# Run all tests
node --test node/tests/**/*.test.mjs

# Run unit tests only
node --test node/tests/unit/*.test.mjs

# Run integration tests only
node --test node/tests/integration/*.test.mjs

# Run specific test file
node --test node/tests/unit/config.test.mjs
```

## Architecture

Follows SOLID principles with clear separation of concerns:
- **config.mjs**: Environment and configuration parsing
- **server.mjs**: HTTP server lifecycle management
- **router.mjs**: Request routing with middleware pattern
- **routes.mjs**: OpenAI API route handlers
- **http-utils.mjs**: Header forwarding and body parsing
- **logger.mjs**: Structured JSON logging

## Test Coverage

- **41 tests** covering all modules
- **35 unit tests**: Isolated component testing with mocks
- **6 integration tests**: End-to-end request/response flows and environment configuration
