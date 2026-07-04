// Drives an Odoo web session with Playwright and captures screenshots for
// each flow defined in a scenario config. Fully parameterized: no URLs, DBs
// or credentials are hardcoded here.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

async function runStep(page, baseUrl, step) {
    const timeout = step.timeout || 15000;
    if (step.goto) {
        await page.goto(`${baseUrl}${step.goto}`, { waitUntil: "domcontentloaded" });
    }
    if (step.waitFor) {
        await page.waitForSelector(step.waitFor, { timeout });
    }
    if (step.fill) {
        await page.fill(step.fill, step.value ?? "");
    }
    if (step.type) {
        // Types character by character so live widgets (autocomplete) react.
        await page.locator(step.type).pressSequentially(step.value ?? "", { delay: 30 });
    }
    if (step.scrollTo) {
        // Scrolls the element into view (Odoo forms scroll inside .o_content,
        // so fullPage screenshots don't reach content below the fold).
        await page.locator(step.scrollTo).first().scrollIntoViewIfNeeded({ timeout });
    }
    if (step.selectOption) {
        // Native <select> widgets (Odoo widget="selection"). Choose by visible
        // label when given, otherwise by option value.
        const opt = step.label !== undefined ? { label: step.label } : { value: step.value };
        await page.selectOption(step.selectOption, opt, { timeout });
    }
    if (step.click) {
        await page.click(step.click, { timeout });
    }
    if (step.hover) {
        // Parks the mouse on a neutral element (e.g. the breadcrumb) so no
        // row/cell tooltip is open when the screenshot is taken.
        await page.locator(step.hover).first().hover({ timeout });
    }
    if (step.press) {
        await page.keyboard.press(step.press);
    }
    if (step.waitForHidden) {
        await page.waitForSelector(step.waitForHidden, { state: "hidden", timeout });
    }
    if (typeof step.wait === "number") {
        await page.waitForTimeout(step.wait);
    }
}

// Captures all flows of `config` against `conn` ({url, db, user, password}).
// Returns { captured, failed }. Throws on authentication failure.
export async function capture(config, conn, imgDir, { headed = false, channel } = {}) {
    mkdirSync(imgDir, { recursive: true });

    // Bundled Chromium by default; pass channel ("chrome") to use a system
    // browser instead, as the original odoo_pro_19 tool did.
    const launchOpts = { headless: !headed };
    if (channel) launchOpts.channel = channel;
    const browser = await chromium.launch(launchOpts);
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,
    });
    const page = await context.newPage();

    try {
        // Authenticate via JSON-RPC; the session cookie is stored on the
        // context and reused by page navigations. This requires the user's
        // real password (an XML-RPC api_key does not open a web session).
        const authResp = await context.request.post(`${conn.url}/web/session/authenticate`, {
            headers: { "Content-Type": "application/json" },
            data: {
                jsonrpc: "2.0",
                method: "call",
                params: { db: conn.db, login: conn.user, password: conn.password },
            },
        });
        const authJson = await authResp.json();
        if (!authJson.result || !authJson.result.uid) {
            throw new Error(
                `Authentication failed on ${conn.url} (db=${conn.db}, user=${conn.user}): ` +
                    JSON.stringify(authJson.error || authJson)
            );
        }
        console.log(`Authenticated as uid ${authJson.result.uid} on ${conn.db}`);

        let captured = 0;
        let failed = 0;
        for (const flow of config.flows || []) {
            if (flow.image === false) {
                continue; // text-only flow, no screenshot
            }
            try {
                for (const step of flow.steps || []) {
                    await runStep(page, conn.url, step);
                }
                await page.waitForTimeout(600);
                const path = join(imgDir, `${flow.id}.png`);
                if (flow.screenshotEl) {
                    const el = await page.$(flow.screenshotEl);
                    if (el) {
                        await el.screenshot({ path });
                    } else {
                        await page.screenshot({ path, fullPage: true });
                    }
                } else {
                    await page.screenshot({ path, fullPage: true });
                }
                captured += 1;
                console.log("captured", `${flow.id}.png`);
            } catch (error) {
                failed += 1;
                console.warn(`flow ${flow.id} failed: ${error.message}`);
            }
        }
        return { captured, failed };
    } finally {
        await browser.close();
    }
}
