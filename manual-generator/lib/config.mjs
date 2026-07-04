// Scenario config loading and schema validation. Validation runs BEFORE any
// browser or seed work so schema mistakes fail fast with a clear message
// instead of producing undefined.png captures or "# undefined" manuals.
import { readFileSync } from "node:fs";

// Throws with a field-precise message when the config is invalid.
export function validateConfig(config, source = "config") {
    const errors = [];
    if (!config || typeof config !== "object" || Array.isArray(config)) {
        throw new Error(`Invalid scenario config ${source}: expected a JSON object`);
    }
    if (!config.module && !config.title) {
        errors.push('missing "module" (or at least "title")');
    }
    if (!config.title) {
        errors.push('missing "title" (used as the manual heading)');
    }
    if (!Array.isArray(config.flows)) {
        errors.push('"flows" must be an array');
    } else {
        const seen = new Set();
        config.flows.forEach((flow, i) => {
            const label = `flows[${i}]`;
            if (!flow || typeof flow !== "object") {
                errors.push(`${label}: expected an object`);
                return;
            }
            if (typeof flow.id !== "string" || !flow.id.trim()) {
                errors.push(`${label}: missing "id" (screenshot filename: <id>.png)`);
            } else if (seen.has(flow.id)) {
                errors.push(`${label}: duplicate "id" "${flow.id}" (would overwrite ${flow.id}.png)`);
            } else {
                seen.add(flow.id);
            }
            if (typeof flow.title !== "string" || !flow.title.trim()) {
                errors.push(`${label}${flow.id ? ` (${flow.id})` : ""}: missing "title"`);
            }
        });
    }
    if (errors.length) {
        throw new Error(`Invalid scenario config ${source}:\n  - ${errors.join("\n  - ")}`);
    }
    return config;
}

export function loadConfig(configPath) {
    let raw;
    try {
        raw = JSON.parse(readFileSync(configPath, "utf8"));
    } catch (error) {
        throw new Error(`Cannot read scenario config ${configPath}: ${error.message}`);
    }
    return validateConfig(raw, configPath);
}
