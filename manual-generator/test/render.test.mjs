import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { render } from "../lib/render.mjs";

let dir;

beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "mg-render-"));
});

afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
});

const config = () => ({
    module: "mod",
    title: "Manual mod",
    flows: [{ id: "f1", title: "Pantalla 1" }],
});

test("references images relative to the manual when imgDir is a sibling img/", () => {
    const imgDir = join(dir, "img");
    mkdirSync(imgDir);
    writeFileSync(join(imgDir, "f1.png"), "png");
    const out = render(config(), imgDir, join(dir, "manual-mod.md"));
    assert.match(readFileSync(out, "utf8"), /!\[Pantalla 1\]\(img\/f1\.png\)/);
});

test("computes the relative path when imgDir is not a sibling", () => {
    const imgDir = join(dir, "assets", "shots");
    mkdirSync(imgDir, { recursive: true });
    writeFileSync(join(imgDir, "f1.png"), "png");
    const outDir = join(dir, "docs");
    const out = render(config(), imgDir, join(outDir, "manual-mod.md"));
    assert.match(readFileSync(out, "utf8"), /!\[Pantalla 1\]\(\.\.\/assets\/shots\/f1\.png\)/);
});

test("emits a pending-capture placeholder when the screenshot is missing", () => {
    const out = render(config(), join(dir, "img"), join(dir, "manual-mod.md"));
    assert.match(readFileSync(out, "utf8"), /captura pendiente/);
});

test("creates the output directory when it does not exist", () => {
    const out = render(config(), null, join(dir, "deep", "nested", "manual-mod.md"));
    assert.match(readFileSync(out, "utf8"), /# Manual mod/);
});
