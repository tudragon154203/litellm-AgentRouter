import assert from "node:assert";
import { test } from "node:test";
import { fetchLatestVersion, DEFAULT_USER_AGENT } from "../../lib/fetch/fetchVersion.mjs";

// Mock the global fetch function
global.fetch = async (url) => {
    if (url === 'https://api.github.com/repos/QwenLM/qwen-code/releases/latest') {
        return {
            ok: true,
            json: async () => ({
                tag_name: 'v1.0.0'
            })
        };
    }
    throw new Error('Unexpected URL');
};

test("fetchLatestVersion returns correct user agent format", async () => {
    const userAgent = await fetchLatestVersion();
    assert.ok(userAgent.includes("QwenCode/v1.0.0"));
    assert.ok(userAgent.includes("("));
    assert.ok(userAgent.includes(")"));
});

test("fetchLatestVersion handles API errors", async () => {
    // Mock fetch to return an error response
    global.fetch = async () => ({
        ok: false,
        status: 404
    });
    
    const userAgent = await fetchLatestVersion();
    assert.ok(userAgent.includes("QwenCode/0.2.0"));
});

test("fetchLatestVersion handles network errors", async () => {
    // Mock fetch to throw an error
    global.fetch = async () => {
        throw new Error("Network error");
    };
    
    const userAgent = await fetchLatestVersion();
    assert.ok(userAgent.includes("QwenCode/0.2.0"));
});

test("DEFAULT_USER_AGENT is properly initialized", () => {
    assert.ok(DEFAULT_USER_AGENT.includes("QwenCode"));
    assert.ok(typeof DEFAULT_USER_AGENT === "string");
});