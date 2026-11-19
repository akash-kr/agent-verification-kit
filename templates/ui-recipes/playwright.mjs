// UI evidence with Playwright: one real recording, screenshots at desktop and phone width, and the
// console errors and failed requests the flow produced.
// Usage: node playwright.mjs <url> <out-dir>      HEADED=1 to watch it in a window (default: headless)
import { chromium } from "playwright";
import { mkdirSync, renameSync, writeFileSync } from "node:fs";

const [url, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ headless: !process.env.HEADED });
const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, recordVideo: { dir: out, size: { width: 1280, height: 800 } } });
const page = await context.newPage();
const consoleErrors = [], failed = [];
page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
page.on("pageerror", (e) => consoleErrors.push(String(e)));
page.on("response", (r) => r.status() >= 400 && failed.push(`${r.status()} ${r.request().method()} ${r.url()}`));
page.on("requestfailed", (r) => failed.push(`failed ${r.method()} ${r.url()}`));

await page.goto(url, { waitUntil: "networkidle" });

// TODO(you): the steps of the flow under test, e.g.
//   await page.getByRole("button", { name: "Sign in" }).click();

await page.screenshot({ path: `${out}/desktop.png` });
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({ path: `${out}/phone.png` });
const video = page.video();
await context.close(); // the recording is written when the context closes
renameSync(await video.path(), `${out}/flow.webm`);
await browser.close();
writeFileSync(`${out}/console.txt`, consoleErrors.join("\n"));
writeFileSync(`${out}/failed-requests.txt`, failed.join("\n"));
console.log(["flow.webm", "desktop.png", "phone.png", "console.txt", "failed-requests.txt"].join("\n"));
