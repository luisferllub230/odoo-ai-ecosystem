import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { validateConfig, loadConfig } from "../lib/config.mjs";

const CONFIGS_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "configs");

const valid = () => ({
    module: "mod",
    title: "Manual mod",
    flows: [
        { id: "f1", title: "Pantalla 1" },
        { id: "f2", title: "Pantalla 2" },
    ],
});

test("accepts a valid config and returns it", () => {
    const cfg = valid();
    assert.equal(validateConfig(cfg), cfg);
});

test("rejects a config without module and title", () => {
    const cfg = valid();
    delete cfg.module;
    delete cfg.title;
    assert.throws(() => validateConfig(cfg), /missing "module"/);
});

test("rejects a flow without id", () => {
    const cfg = valid();
    delete cfg.flows[0].id;
    assert.throws(() => validateConfig(cfg), /flows\[0\]: missing "id"/);
});

test("rejects duplicate flow ids", () => {
    const cfg = valid();
    cfg.flows[1].id = "f1";
    assert.throws(() => validateConfig(cfg), /duplicate "id" "f1"/);
});

test("rejects a flow without title", () => {
    const cfg = valid();
    cfg.flows[1].title = "  ";
    assert.throws(() => validateConfig(cfg), /flows\[1\] \(f2\): missing "title"/);
});

test("rejects non-array flows", () => {
    const cfg = valid();
    cfg.flows = {};
    assert.throws(() => validateConfig(cfg), /"flows" must be an array/);
});

test("loadConfig reports unreadable/invalid JSON with the path", () => {
    assert.throws(() => loadConfig("/nonexistent/x.json"), /Cannot read scenario config \/nonexistent\/x\.json/);
});

test("all shipped configs pass validation", () => {
    const shipped = readdirSync(CONFIGS_DIR).filter((f) => f.endsWith(".json"));
    assert.ok(shipped.length >= 11, `expected the shipped configs, got ${shipped.length}`);
    for (const file of shipped) {
        assert.doesNotThrow(() => loadConfig(join(CONFIGS_DIR, file)), `config ${file} should be valid`);
    }
});
