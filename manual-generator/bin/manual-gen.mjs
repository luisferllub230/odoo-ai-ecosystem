#!/usr/bin/env node
// manual-gen — single CLI for the standalone Odoo manual generator.
//
// Subcommands:
//   capture --config <scenario.json> [--profile <p> | --url --db --user] [opts]
//   render  --config <scenario.json> [--out <dir>]
//   run     capture + render
//
// Connection: --profile reads conector-odoo/profiles.yml (secrets expanded
// from env via ${VAR}); explicit flags override profile values. The UI
// password comes ONLY from env (ODOO_UI_PASSWORD or the profile's
// ui_password ${VAR} reference) — never from flags or files.
import { existsSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { parseArgs } from "../lib/args.mjs";
import { loadConfig } from "../lib/config.mjs";
import { capture } from "../lib/capture.mjs";
import { render } from "../lib/render.mjs";
import { resolveConnection } from "../lib/profiles.mjs";
import { runSeed, defaultSeedPath } from "../lib/seed.mjs";

const USAGE = `Usage: manual-gen <capture|render|run> --config <scenario.json> [options]

Options:
  --config <file>         Scenario JSON (required)
  --out <dir>             Output dir (default: the config's folder).
                          Manual: <out>/manual-<module>.md  Images: <out>/img/
  --profile <name>        Connection profile from conector-odoo/profiles.yml
  --profiles-file <file>  Alternative profiles.yml (or env MANUAL_GEN_PROFILES)
  --url <url>             Odoo base URL (overrides profile)
  --db <name>             Database (overrides profile)
  --user <login>          Login user (overrides profile)
  --headed                Show the browser (debug); headless by default
  --channel <name>        Playwright browser channel (e.g. "chrome"); default
                          is the bundled Chromium
  --compose-dir <dir>     F4 environment dir; enables seeding via
                          "docker compose exec odoo odoo shell"
  --seed <file>           Seed script (default: <config>.seed.py; for
                          <base>.before/.after.json also <base>.seed.py)
  --no-seed               Skip seeding even if a seed file exists
  --allow-partial         Exit 0 even if some flows failed to capture
                          (default is strict: any failed flow => exit 1)

Password: set ODOO_UI_PASSWORD (or the env var referenced by the profile's
ui_password). A web UI login needs a real user password; XML-RPC api keys
do not work for it.`;

async function main() {
    const [command, ...rest] = process.argv.slice(2);
    let args;
    try {
        args = parseArgs(rest);
    } catch (error) {
        console.error(`${error.message}\n\n${USAGE}`);
        process.exit(2);
    }

    if (!command || args.help || command === "help") {
        console.log(USAGE);
        process.exit(command ? 0 : 2);
    }
    if (!["capture", "render", "run"].includes(command)) {
        console.error(`Unknown command: ${command}\n\n${USAGE}`);
        process.exit(2);
    }
    if (!args.config) {
        console.error(`Missing --config\n\n${USAGE}`);
        process.exit(2);
    }

    const configPath = resolve(args.config);
    if (!existsSync(configPath)) {
        console.error(`Config not found: ${configPath}`);
        process.exit(2);
    }
    // Validates the schema (module/title, unique flow ids, flow titles)
    // BEFORE any connection, seed or browser work.
    let config;
    try {
        config = loadConfig(configPath);
    } catch (error) {
        console.error(error.message);
        process.exit(2);
    }
    const moduleName = config.module || "manual";
    const outDir = resolve(args.out || dirname(configPath));
    const imgDir = join(outDir, "img");
    const manualPath = join(outDir, `manual-${moduleName}.md`);

    let exitCode = 0;

    if (command === "capture" || command === "run") {
        const conn = resolveConnection({
            profile: args.profile,
            profilesFile: args["profiles-file"],
            url: args.url,
            db: args.db,
            user: args.user,
        });

        // Seed (optional; only for local docker compose targets). The seed
        // status is always logged so a skipped seed is never silent.
        if (args["no-seed"]) {
            console.log("seed: skipped (--no-seed)");
        } else {
            const seedFile = args.seed ? resolve(args.seed) : defaultSeedPath(configPath);
            if (args.seed && !existsSync(seedFile)) {
                throw new Error(`Seed file not found: ${seedFile} (from --seed)`);
            }
            if (!seedFile) {
                console.log("seed: none found for this config — continuing without seed data");
            } else if (args["compose-dir"]) {
                console.log(`seed: ${seedFile}`);
                runSeed(seedFile, conn.db, resolve(args["compose-dir"]));
            } else {
                console.warn(
                    `WARNING: seed file ${seedFile} found but no --compose-dir given; ` +
                        "skipping seed. Seeds run via 'odoo shell' inside a local docker " +
                        "compose environment (F4). Pass --compose-dir <dir> or --no-seed."
                );
            }
        }

        const { captured, failed } = await capture(config, conn, imgDir, {
            headed: !!args.headed,
            channel: args.channel,
        });
        console.log(`Capture done. captured=${captured} failed=${failed}`);
        if (failed > 0) {
            if (args["allow-partial"] && captured > 0) {
                console.warn(`WARNING: ${failed} flow(s) failed (--allow-partial: exiting 0)`);
            } else {
                exitCode = 1;
            }
        }
    }

    if (command === "render" || command === "run") {
        const written = render(config, imgDir, manualPath);
        console.log("wrote", written);
    }

    process.exit(exitCode);
}

main().catch((error) => {
    console.error(error.message || error);
    process.exit(1);
});
