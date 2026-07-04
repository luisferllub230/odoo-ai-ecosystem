// Seed execution. Seed scripts are Python files run inside `odoo shell`
// (the `env` global is provided; they end with env.cr.commit()), exactly as
// the original odoo_pro_19 tool ran them. That mechanism only works when the
// target Odoo is a local docker compose environment (F4), so seeding is
// opt-in via --compose-dir. For remote instances, pre-seed the data by other
// means (or extend the scenario steps to create it through the UI).
import { spawnSync } from "node:child_process";
import { existsSync, openSync, closeSync } from "node:fs";

// Default seed file convention: <config>.json -> <config>.seed.py. Variant
// configs named <base>.before.json / <base>.after.json share the base seed
// (<base>.seed.py), so when the exact match is missing we fall back to it.
// Returns the path of an EXISTING seed file, or null when none applies.
export function defaultSeedPath(configPath) {
    const primary = configPath.replace(/\.json$/, ".seed.py");
    if (existsSync(primary)) return primary;
    const variant = configPath.match(/^(.*)\.(before|after)\.json$/);
    if (variant) {
        const fallback = `${variant[1]}.seed.py`;
        if (existsSync(fallback)) return fallback;
    }
    return null;
}

// Runs `docker compose exec -T odoo odoo shell -d <db>` in composeDir with
// the seed file on stdin. The F4 template's conf/odoo.conf already carries
// the DB credentials, so no --db_* flags are needed.
export function runSeed(seedFile, db, composeDir) {
    if (!existsSync(seedFile)) {
        throw new Error(`Seed file not found: ${seedFile}`);
    }
    console.log(`Seeding ${db} with ${seedFile} (compose dir: ${composeDir})`);
    const fd = openSync(seedFile, "r");
    try {
        const res = spawnSync(
            "docker",
            ["compose", "exec", "-T", "odoo", "odoo", "shell", "-d", db, "--no-http", "--log-level=error"],
            { cwd: composeDir, stdio: [fd, "inherit", "inherit"] }
        );
        if (res.error) {
            throw new Error(`Failed to run docker compose: ${res.error.message}`);
        }
        if (res.status !== 0) {
            throw new Error(`Seed execution failed (exit ${res.status})`);
        }
    } finally {
        closeSync(fd);
    }
}
