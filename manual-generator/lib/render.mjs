// Renders the markdown manual from a scenario config and the screenshots
// captured by capture.mjs. Image references are relative (img/<id>.png) so
// the manual can be attached to Odoo tasks or PRs together with its folder.
import { writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname, relative, sep } from "node:path";

// Returns the path of the written manual.
export function render(config, imgDir, outPath) {
    // Image links are computed relative to the manual's own folder (posix
    // separators) so the folder stays portable wherever imgDir lives.
    const relImgDir = imgDir
        ? relative(dirname(outPath), imgDir).split(sep).join("/") || "."
        : "img";
    const lines = [];
    lines.push(`# ${config.title}`, "");
    lines.push(
        "> Manual generado con `manual-generator` (odoo-ai-ecosystem). " +
            "Las capturas se regeneran ejecutando `manual-gen run` contra la instancia objetivo.",
        ""
    );
    if (config.intro) {
        lines.push(config.intro, "");
    }
    if (config.requirements && config.requirements.length) {
        lines.push("## Requisitos previos", "");
        for (const req of config.requirements) {
            lines.push(`- ${req}`);
        }
        lines.push("");
    }
    for (const flow of config.flows || []) {
        lines.push(`## ${flow.title}`, "");
        if (flow.description) {
            lines.push(flow.description, "");
        }
        if (flow.image !== false) {
            const file = `${flow.id}.png`;
            if (imgDir && existsSync(join(imgDir, file))) {
                lines.push(`![${flow.title}](${relImgDir}/${file})`, "");
            } else {
                lines.push("> _(captura pendiente: ejecutar `manual-gen capture`)_", "");
            }
        }
    }
    if (config.notes) {
        lines.push("## Notas", "");
        lines.push(config.notes, "");
    }

    mkdirSync(dirname(outPath), { recursive: true });
    writeFileSync(outPath, lines.join("\n"));
    return outPath;
}
