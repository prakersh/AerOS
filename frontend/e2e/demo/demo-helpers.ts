import { type Page } from "@playwright/test";

/** Readability pause for the recording. */
export async function beat(page: Page, ms = 1500): Promise<void> {
  await page.waitForTimeout(ms);
}

/**
 * Full-screen interstitial slide shown BETWEEN steps (never over live UI).
 * Labels the step number, the actor, and which account is logged in.
 */
export async function titleCard(
  page: Page,
  opts: { step: string; actor: string; account?: string; text: string; accent?: string },
  ms = 3200,
): Promise<void> {
  await page.evaluate((o) => {
    let el = document.getElementById("aeros-title-card");
    if (!el) {
      el = document.createElement("div");
      el.id = "aeros-title-card";
      document.body.appendChild(el);
    }
    el.style.cssText = [
      "position:fixed",
      "inset:0",
      "z-index:2147483647",
      "display:flex",
      "flex-direction:column",
      "align-items:center",
      "justify-content:center",
      "gap:20px",
      "background:radial-gradient(circle at 50% 38%, #1e1b4b 0%, #09090b 70%)",
      "color:#fff",
      "font-family:system-ui,-apple-system,Segoe UI,sans-serif",
      "text-align:center",
      "padding:48px",
    ].join(";");
    const accent = o.accent || "#818cf8";
    el.innerHTML =
      `<div style="font-size:14px;font-weight:700;letter-spacing:.3em;text-transform:uppercase;color:#a5b4fc">${o.step}</div>` +
      `<div style="font-size:44px;font-weight:700;max-width:1040px;line-height:1.2">${o.text}</div>` +
      `<div style="display:inline-flex;align-items:center;gap:12px;margin-top:6px;padding:10px 22px;border-radius:999px;background:rgba(255,255,255,.08);font-size:17px">` +
      `<span style="font-weight:600;color:${accent}">${o.actor}</span>` +
      (o.account
        ? `<span style="opacity:.5">·</span><span style="opacity:.85;font-family:ui-monospace,monospace">${o.account}</span>`
        : "") +
      `</div>`;
  }, opts);
  await page.waitForTimeout(ms);
  await page.evaluate(() => document.getElementById("aeros-title-card")?.remove());
  await page.waitForTimeout(300);
}

/**
 * Wait for one co-pilot turn to finish. Endpoint-agnostic: watches the DOM
 * typing indicator (bouncing dots) appear then disappear.
 */
export async function waitForCopilotReply(page: Page, pauseMs = 2500): Promise<void> {
  const dots = page.locator(".animate-bounce").first();
  await dots.waitFor({ state: "visible", timeout: 8000 }).catch(() => {});
  await dots.waitFor({ state: "hidden", timeout: 120000 }).catch(() => {});
  await page.waitForLoadState("networkidle").catch(() => {});
  await beat(page, pauseMs);
}

/** Navigate via the sidebar link when possible, else direct goto. */
export async function nav(page: Page, label: string, fallbackPath: string): Promise<void> {
  const link = page.getByRole("link", { name: label, exact: true }).first();
  if (await link.isVisible().catch(() => false)) {
    await link.click();
  } else {
    await page.goto(fallbackPath);
  }
  await page.waitForLoadState("networkidle").catch(() => {});
  await beat(page, 1500);
}

/** Single smooth downward pass for the camera — no jittery scroll-back. */
export async function scrollThrough(page: Page, total = 1600, steps = 7): Promise<void> {
  const per = Math.round(total / steps);
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, per);
    await beat(page, 550);
  }
}
