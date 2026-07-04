// CLI argument parsing. Supports "--name value" and "--name=value"; boolean
// flags take no value. Throws on malformed input; the bin turns that into a
// usage error (exit 2).
const BOOLEAN_FLAGS = new Set(["headed", "no-seed", "allow-partial", "help"]);

export function parseArgs(argv) {
    const args = { _: [] };
    for (let i = 0; i < argv.length; i++) {
        let a = argv[i];
        if (!a.startsWith("--")) {
            args._.push(a);
            continue;
        }
        a = a.slice(2);
        const eq = a.indexOf("=");
        if (eq !== -1) {
            args[a.slice(0, eq)] = a.slice(eq + 1);
        } else if (BOOLEAN_FLAGS.has(a)) {
            args[a] = true;
        } else {
            const next = argv[i + 1];
            if (next === undefined || next.startsWith("--")) {
                throw new Error(`Missing value for --${a}`);
            }
            args[a] = next;
            i++;
        }
    }
    return args;
}
