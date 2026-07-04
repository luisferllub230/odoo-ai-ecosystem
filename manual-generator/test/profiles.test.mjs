import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { expandEnv, resolveConnection } from "../lib/profiles.mjs";

let dir;
let profilesFile;
const ENV_KEYS = ["MG_TEST_URL", "MG_TEST_PASS", "ODOO_UI_PASSWORD"];
const saved = {};

function writeProfiles(yaml) {
    writeFileSync(profilesFile, yaml);
}

beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "mg-profiles-"));
    profilesFile = join(dir, "profiles.yml");
    for (const k of ENV_KEYS) {
        saved[k] = process.env[k];
        delete process.env[k];
    }
});

afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
    for (const k of ENV_KEYS) {
        if (saved[k] === undefined) delete process.env[k];
        else process.env[k] = saved[k];
    }
});

test("expandEnv: passes literals through, expands set vars, undefined for unset vars", () => {
    assert.equal(expandEnv("plain"), "plain");
    process.env.MG_TEST_URL = "http://x:1";
    assert.equal(expandEnv("${MG_TEST_URL}"), "http://x:1");
    assert.equal(expandEnv("pre-${MG_TEST_URL}-post"), "pre-http://x:1-post");
    assert.equal(expandEnv("${MG_UNSET_VAR_XYZ}"), undefined);
    assert.equal(expandEnv(42), 42);
});

test("profile provides url/db/user; ui_password ${VAR} resolves from env", () => {
    writeProfiles('p:\n  url: http://odoo:8069/\n  db: mydb\n  user: admin\n  ui_password: "${MG_TEST_PASS}"\n');
    process.env.MG_TEST_PASS = "s3cret";
    const conn = resolveConnection({ profile: "p", profilesFile });
    assert.equal(conn.url, "http://odoo:8069"); // trailing slash stripped
    assert.equal(conn.db, "mydb");
    assert.equal(conn.user, "admin");
    assert.equal(conn.password, "s3cret");
});

test("explicit flags override profile values", () => {
    writeProfiles("p:\n  url: http://odoo:8069\n  db: mydb\n  user: admin\n");
    process.env.ODOO_UI_PASSWORD = "pw";
    const conn = resolveConnection({
        profile: "p",
        profilesFile,
        url: "http://other:9999",
        db: "otherdb",
        user: "demo",
    });
    assert.equal(conn.url, "http://other:9999");
    assert.equal(conn.db, "otherdb");
    assert.equal(conn.user, "demo");
});

test("ODOO_UI_PASSWORD is the fallback when the profile has no ui_password", () => {
    writeProfiles("p:\n  url: http://odoo:8069\n  db: mydb\n  user: admin\n");
    process.env.ODOO_UI_PASSWORD = "envpw";
    const conn = resolveConnection({ profile: "p", profilesFile });
    assert.equal(conn.password, "envpw");
});

test("missing password fails with the api_key hint", () => {
    writeProfiles("p:\n  url: http://odoo:8069\n  db: mydb\n  user: admin\n");
    assert.throws(
        () => resolveConnection({ profile: "p", profilesFile }),
        /api_key does NOT work for web UI login/
    );
});

test("literal ui_password in profiles.yml is rejected (secrets contract)", () => {
    writeProfiles("p:\n  url: http://odoo:8069\n  db: mydb\n  user: admin\n  ui_password: hunter2\n");
    process.env.ODOO_UI_PASSWORD = "irrelevant";
    assert.throws(
        () => resolveConnection({ profile: "p", profilesFile }),
        /ui_password must be a \$\{VAR\} env reference, never a literal/
    );
});

test("partial ${VAR} mixed with literal text is also rejected", () => {
    writeProfiles('p:\n  url: http://odoo:8069\n  db: mydb\n  user: admin\n  ui_password: "pw-${MG_TEST_PASS}"\n');
    process.env.MG_TEST_PASS = "x";
    assert.throws(() => resolveConnection({ profile: "p", profilesFile }), /never a literal/);
});

test("missing url/db/user reports the missing fields", () => {
    writeProfiles("p:\n  url: http://odoo:8069\n");
    process.env.ODOO_UI_PASSWORD = "pw";
    assert.throws(() => resolveConnection({ profile: "p", profilesFile }), /Missing connection settings: db, user/);
});

test("unknown profile lists the available ones", () => {
    writeProfiles("gestor:\n  url: http://x\n");
    assert.throws(() => resolveConnection({ profile: "nope", profilesFile }), /Available: gestor/);
});
