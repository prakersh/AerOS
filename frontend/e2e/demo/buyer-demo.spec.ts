import { test } from "@playwright/test";
import { loginAsBuyer } from "../helpers";
import { caption, clearCaption, beat, waitForCopilotReply } from "./demo-helpers";

// Prompts chosen to reliably trigger tool-backed visual replies (tables/cards).
const PROMPTS = [
  "List the vendors that can supply dairy and produce.",
  "Evaluate the offers for RFx #1 and show me the side-by-side comparison.",
];

test("buyer co-pilot replies with interactive tables", async ({ page }) => {
  test.setTimeout(240000);

  await loginAsBuyer(page);
  await page.waitForLoadState("networkidle");
  await caption(page, "AEROS — Buyer Co-pilot", "The agent replies visually, not just in text");
  await beat(page, 2500);

  await caption(page, "Step 1 — Open the AI co-pilot", "Ask in plain language");
  await page.goto("/buyer/chat");
  const input = page.locator('input[placeholder*="procurement"]');
  await input.waitFor({ state: "visible", timeout: 15000 });
  await beat(page, 1500);

  // Turn 1 — vendor table
  await caption(page, "Step 2 — Ask for vendors", "Co-pilot answers with a live table");
  await input.click();
  await input.fill(PROMPTS[0]);
  await beat(page, 1000);
  await input.press("Control+Enter");
  await waitForCopilotReply(page, 2500);
  await page.mouse.wheel(0, 1400);
  await beat(page, 3000);

  // Turn 2 — comparison table
  await caption(page, "Step 3 — Ask for a comparison", "Side-by-side matrix, lowest price highlighted");
  await input.click();
  await input.fill(PROMPTS[1]);
  await beat(page, 1000);
  await input.press("Control+Enter");
  await waitForCopilotReply(page, 3500);
  await page.mouse.wheel(0, 1800);
  await beat(page, 3500);

  // The comparison block carries an action button → open the full matrix.
  const openBtn = page.getByRole("button", { name: /Open full comparison/i }).first();
  if (await openBtn.isVisible().catch(() => false)) {
    await clearCaption(page);
    await caption(page, "Step 4 — One click to the full matrix", "Per-line-item split award");
    await openBtn.scrollIntoViewIfNeeded();
    await beat(page, 1500);
    await openBtn.click();
    await page.waitForLoadState("networkidle");
    await beat(page, 3000);
  }

  await caption(page, "AEROS", "Agents that reply with tables, cards & actions.");
  await beat(page, 3000);
  await clearCaption(page);
});
