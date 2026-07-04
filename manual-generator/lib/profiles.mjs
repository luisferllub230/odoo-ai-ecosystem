// Loads connection profiles from conector-odoo's profiles.yml (or any YAML
// file with the same shape) and resolves the effective connection for a run.
//
// Profile shape (secrets are NEVER stored in the file — only ${VAR} refs):
//   <name>:
//     url: http://host:port
//     db: database
//     user: login
//     api_key: ${SOME_KEY}        # used by conector-odoo (XML-RPC); NOT valid for UI login
//     ui_password: ${SOME_PASS}   # optional: env var holding the UI password
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import YAML from "yaml";

const PKG_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");

// Expands ${VAR} references from the environment. Unset vars resolve to
// undefined so callers can tell "missing secret" apart from empty string.
export function expandEnv(value) {
    if (typeof value !== "string") return value;
    let missing = false;
    const expanded = value.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, name) => {
        if (process.env[name] === undefined) {
            missing = true;
            return "";
        }
        return process.env[name];
    });
    return missing ? undefined : expanded;
}

// Resolution order: explicit flag > MANUAL_GEN_PROFILES env > sibling
// conector-odoo/profiles.yml (manual-generator lives next to conector-odoo
// inside odoo-ai-ecosystem).
export function findProfilesFile(explicitPath) {
    const candidates = [
        explicitPath,
        process.env.MANUAL_GEN_PROFILES,
        join(PKG_DIR, "..", "conector-odoo", "profiles.yml"),
    ].filter(Boolean);
    for (const candidate of candidates) {
        const abs = resolve(candidate);
        if (existsSync(abs)) return abs;
    }
    throw new Error(
        `profiles.yml not found (tried: ${candidates.join(", ")}). ` +
            "Pass --profiles-file or set MANUAL_GEN_PROFILES."
    );
}

export function loadProfile(name, profilesPath) {
    const file = findProfilesFile(profilesPath);
    const doc = YAML.parse(readFileSync(file, "utf8")) || {};
    const profile = doc[name];
    if (!profile) {
        const available = Object.keys(doc).join(", ") || "(none)";
        throw new Error(`Profile "${name}" not found in ${file}. Available: ${available}`);
    }
    return { ...profile, _file: file };
}

// Secrets contract: ui_password in profiles.yml must be a single ${VAR}
// env reference, never a literal value (the file is versionable).
const ENV_REF_RE = /^\$\{[A-Za-z_][A-Za-z0-9_]*\}$/;

// Merges profile values with explicit flags (flags win) and resolves the UI
// password. The password NEVER comes from flags or config files: only from
// the env var referenced by the profile's ui_password, or ODOO_UI_PASSWORD.
export function resolveConnection({ profile, profilesFile, url, db, user }) {
    let base = {};
    if (profile) {
        base = loadProfile(profile, profilesFile);
    }
    if (base.ui_password !== undefined && !ENV_REF_RE.test(String(base.ui_password))) {
        throw new Error(
            `Profile "${profile}" (${base._file}): ui_password must be a \${VAR} env ` +
                "reference, never a literal secret in profiles.yml. Move the password " +
                'to an env var and reference it, e.g. ui_password: "${MY_ODOO_PASSWORD}".'
        );
    }
    const conn = {
        url: (url || expandEnv(base.url) || "").replace(/\/+$/, ""),
        db: db || expandEnv(base.db),
        user: user || expandEnv(base.user),
        password: expandEnv(base.ui_password) ?? process.env.ODOO_UI_PASSWORD,
    };
    const missing = ["url", "db", "user"].filter((k) => !conn[k]);
    if (missing.length) {
        throw new Error(
            `Missing connection settings: ${missing.join(", ")}. ` +
                "Provide them via --profile or explicit flags (--url --db --user)."
        );
    }
    if (!conn.password) {
        throw new Error(
            "No UI password available. Set ODOO_UI_PASSWORD (or the env var referenced " +
                "by the profile's ui_password field). Note: an XML-RPC api_key does NOT " +
                "work for web UI login — a real user password is required."
        );
    }
    return conn;
}
