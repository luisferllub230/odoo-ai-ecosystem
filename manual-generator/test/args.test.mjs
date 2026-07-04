import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs } from "../lib/args.mjs";

test("parses --name value pairs", () => {
    const args = parseArgs(["--config", "c.json", "--out", "dir"]);
    assert.equal(args.config, "c.json");
    assert.equal(args.out, "dir");
});

test("parses --name=value pairs", () => {
    const args = parseArgs(["--config=c.json", "--url=http://x:1"]);
    assert.equal(args.config, "c.json");
    assert.equal(args.url, "http://x:1");
});

test("boolean flags take no value", () => {
    const args = parseArgs(["--headed", "--no-seed", "--allow-partial", "--config", "c.json"]);
    assert.equal(args.headed, true);
    assert.equal(args["no-seed"], true);
    assert.equal(args["allow-partial"], true);
    assert.equal(args.config, "c.json");
});

test("collects positionals", () => {
    const args = parseArgs(["extra", "--config", "c.json"]);
    assert.deepEqual(args._, ["extra"]);
});

test("throws on missing value for a non-boolean option", () => {
    assert.throws(() => parseArgs(["--config"]), /Missing value for --config/);
    assert.throws(() => parseArgs(["--config", "--out"]), /Missing value for --config/);
});
