import { type Page } from "@playwright/test";

/**
 * Show a step caption banner overlaid on the page (bottom-centered).
 * Persists across in-page navigation only until the next caption() / clearCaption().
 */
export async function caption(page: Page, title: string, subtitle = ""): Promise<void> {
  await page.evaluate(
    ({ title, subtitle }) => {
      let el = document.getElementById("aeros-demo-caption");
      if (!el) {
        el = document.createElement("div");
        el.id = "aeros-demo-caption";
        document.body.appendChild(el);
      }
      el.style.cssText = [
        "position:fixed",
        "left:50%",
        "bottom:32px",
        "transform:translateX(-50%)",
        "z-index:2147483647",
        "max-width:80%",
        "padding:14px 28px",
        "border-radius:14px",
        "background:linear-gradient(90deg,#4f46e5,#7c3aed)",
        "color:#fff",
        "font-family:system-ui,-apple-system,Segoe UI,sans-serif",
        "box-shadow:0 8px 32px rgba(0,0,0,.45)",
        "text-align:center",
        "pointer-events:none",
      ].join(";");
      el.innerHTML =
        `<div style="font-size:19px;font-weight:600;line-height:1.3">${title}</div>` +
        (subtitle
          ? `<div style="font-size:13px;font-weight:400;opacity:.88;margin-top:3px">${subtitle}</div>`
          : "");
    },
    { title, subtitle },
  );
}

export async function clearCaption(page: Page): Promise<void> {
  await page.evaluate(() => document.getElementById("aeros-demo-caption")?.remove());
}

/** Readability pause for the recording. */
export async function beat(page: Page, ms = 1800): Promise<void> {
  await page.waitForTimeout(ms);
}

/** Wait for one real /api/chat co-pilot turn to complete, then a readability beat. */
export async function waitForCopilotReply(page: Page, pauseMs = 2500): Promise<void> {
  await page
    .waitForResponse((r) => /\/api\/chat$/.test(r.url()) && r.request().method() === "POST", {
      timeout: 120000,
    })
    .catch(() => {
      /* tolerate timeout so the demo keeps rolling */
    });
  await page.waitForLoadState("networkidle").catch(() => {});
  await beat(page, pauseMs);
}
