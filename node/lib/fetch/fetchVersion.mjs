import os from "node:os";

/**
 * Fetches the latest QwenCode CLI version from GitHub releases API
 * @returns {Promise<string>} The user agent string with the latest version
 */
export async function fetchLatestVersion() {
    try {
        const response = await fetch('https://api.github.com/repos/QwenLM/qwen-code/releases/latest');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const latestVersion = data.tag_name;

        // Return the user agent with the latest version
        return `QwenCode/${latestVersion} (${os.platform().toLowerCase()}; ${os.arch()})`;
    } catch (error) {
        console.error('Error fetching latest version:', error);
        // Fallback to the hardcoded version in case of error
        return `QwenCode/0.2.0 (${os.platform().toLowerCase()}; ${os.arch()})`;
    }
}

// Export the default user agent as a promise
export const DEFAULT_USER_AGENT = await fetchLatestVersion();