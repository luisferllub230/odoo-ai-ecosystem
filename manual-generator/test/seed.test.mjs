import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { defaultSeedPath } from "../lib/seed.mjs";

let dir;

beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "mg-seed-"));
});

afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
});

test("returns <base>.seed.py when it exists", () => {
    writeFileSync(join(dir, "mod.seed.py"), "# seed");
    assert.equal(defaultSeedPath(join(dir, "mod.json")), join(dir, "mod.seed.py"));
});

test("<base>.before.json falls back to <base>.seed.py", () => {
    writeFileSync(join(dir, "mod.seed.py"), "# seed");
    assert.equal(defaultSeedPath(join(dir, "mod.before.json")), join(dir, "mod.seed.py"));
});

test("<base>.after.json falls back to <base>.seed.py", () => {
    writeFileSync(join(dir, "mod.seed.py"), "# seed");
    assert.equal(defaultSeedPath(join(dir, "mod.after.json")), join(dir, "mod.seed.py"));
});

test("exact variant seed wins over the base fallback", () => {
    writeFileSync(join(dir, "mod.seed.py"), "# base");
    writeFileSync(join(dir, "mod.before.seed.py"), "# variant");
    assert.equal(defaultSeedPath(join(dir, "mod.before.json")), join(dir, "mod.before.seed.py"));
});

test("returns null when no seed file exists", () => {
    assert.equal(defaultSeedPath(join(dir, "mod.json")), null);
    assert.equal(defaultSeedPath(join(dir, "mod.before.json")), null);
});
