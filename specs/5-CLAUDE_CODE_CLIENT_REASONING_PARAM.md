# REASONING_PARAM.md

## Thinking Mode Reasoning Parameter Behavior

### Overview
When Claude Code uses a model in thinking mode, the `reasoning` parameter gets automatically added to requests by the reasoning transformer in `@musistudio/llms`.

### When Reasoning Parameter is Added
The `reasoning` parameter is injected when:
1. **Thinking mode is enabled** in Claude Code (user invokes thinking/reasoning mode)
2. **Provider configuration includes** the `"reasoning"` transformer
3. **Request passes through** the reasoning transformer

### Parameter Structure
```json
{
  "reasoning": {
    "effort": <number>,    // Token budget for reasoning (from thinking.budget_tokens)
    "enabled": true         // Boolean flag when thinking mode is active
  }
}
```

### Example Full Request
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Help me design a scalable architecture"
    }
  ],
  "model": "gpt-5",
  "max_tokens": 4000,
  "temperature": 0.7,
  "stream": true,
  "reasoning": {
    "effort": 30000,
    "enabled": true
  }
}
```

### Code Location
**Source**: `@musistudio/llms/dist/cjs/server.cjs:68`

```javascript
let s = {
  messages: t,
  model: e.model,
  max_tokens: e.max_tokens,
  temperature: e.temperature,
  stream: e.stream,
  tools: e.tools?.length ? this.convertAnthropicToolsToUnified(e.tools) : void 0,
  tool_choice: e.tool_choice
};

return e.thinking && (s.reasoning = {
  effort: Qf(e.thinking.budget_tokens),
  enabled: e.thinking.type === "enabled"
}),
```

### Problem with Upstream APIs
- The `reasoning` parameter is **NOT part of standard OpenAI API**
- Many upstream APIs (including litellm proxy to gpt-5) reject it as "Unknown parameter"
- Results in 400 errors: `"Unknown parameter: 'reasoning'"`

### Provider Configuration Example
```json
{
  "name": "deepseek",
  "api_base_url": "https://api.deepseek.com/v1",
  "api_key": "your-key",
  "models": ["deepseek-reasoner"],
  "transformer": {
    "use": ["reasoning"]  // This causes reasoning parameter to be added
  }
}
```

### Solutions for Proxy Fix
1. **Remove reasoning parameter** for incompatible upstream APIs
2. **Add conditional logic** to only include `reasoning` for supported models
3. **Transform or strip** the parameter before forwarding to upstream
4. **Add API compatibility checks** based on model/provider

### Detection Logic
To detect thinking mode requests in proxy:
- Check for `req.body.thinking` field
- Look for `reasoning` parameter in transformed request
- Identify models that should/shouldn't receive reasoning parameter

### Implementation Note
The reasoning parameter is intended for specialized reasoning models (like Deepseek Reasoner) but breaks compatibility with standard OpenAI-compatible endpoints.