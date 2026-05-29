import { test } from "@playwright/test";
import { login } from "../helpers";
import { caption, clearCaption, beat } from "./demo-helpers";

const SAMPLE_PRICES = ["28.50", "32.00", "54.75", "46.20", "61.00"];
// Metro FMCG is invited to an OPEN (dispatched) RFx, so a fresh quote can be submitted.
const VENDOR_EMAIL = "metro@vendor.demo";
const VENDOR_PASSWORD = "vendor123";
const QUOTE_FILE = "../tests/fixtures/vendor_quotes/quote_bakery.pdf";

test("vendor co-pilot replies visually, then vendor submits a quote", async ({ page }) => {
  test.setTimeout(180000);

  await login(page, VENDOR_EMAIL, VENDOR_PASSWORD);
  await page.waitForURL("**/vendor/**", { timeout: 15000 });
  await page.goto("/vendor/inbox");
  await page.waitForLoadState("networkidle");
  await caption(page, "AEROS — Vendor Portal", "The co-pilot replies visually here too");
  await beat(page, 2500);

  // --- Open an open invitation ---
  await caption(page, "Step 1 — Open the RFx invitation", "Inbox with live deadlines");
  const inboxItems = page.locator('[data-testid="inbox-item"]');
  await inboxItems.first().waitFor({ state: "visible", timeout: 15000 });
  await beat(page, 1200);
  const openItem = inboxItems.filter({ hasText: "Bakery Supplies" }).first();
  if (await openItem.isVisible().catch(() => false)) {
    await openItem.click();
  } else {
    await inboxItems.first().click();
  }
  await page.waitForURL("**/vendor/rfx/**", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await beat(page, 1500);

  // --- Step 2: upload a quote in any format ---
  await caption(page, "Step 2 — Reply in any format", "PDF · Word · Excel · photo · email");
  const uploadTab = page.getByRole("button", { name: "Upload & Analyze" });
  if (await uploadTab.isVisible().catch(() => false)) {
    await uploadTab.click();
    await beat(page, 1200);
  }
  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.setInputFiles(QUOTE_FILE);
  await page.waitForLoadState("networkidle");

  // --- Step 3: co-pilot visual reply (card + requested-items table) ---
  await caption(page, "Step 3 — Ask the co-pilot", "It answers with a card + items table");
  const askBtn = page.getByRole("button", { name: /Ask AI about this document/i }).first();
  await askBtn.waitFor({ state: "visible", timeout: 30000 });
  await beat(page, 1500);
  const resp = page
    .waitForResponse((r) => /\/api\/chat$/.test(r.url()) && r.request().method() === "POST", {
      timeout: 60000,
    })
    .catch(() => {});
  await askBtn.click();
  await resp;
  await page.waitForLoadState("networkidle").catch(() => {});
  await beat(page, 2000);
  // Clear the caption so it doesn't cover the panel, then center the co-pilot's
  // table block in the scroll container for a clean shot.
  await clearCaption(page);
  const copilotTable = page.locator("table").last();
  if (await copilotTable.isVisible().catch(() => false)) {
    await copilotTable.evaluate((el) => el.scrollIntoView({ block: "center" }));
  } else {
    await page.mouse.wheel(0, 1400);
  }
  await beat(page, 4500);

  // --- Step 4: structured quote + submit ---
  await clearCaption(page);
  await caption(page, "Step 4 — Submit the quote", "Buyer sees it in the comparison matrix");
  const quoteTab = page.getByRole("button", { name: "Quote Form" });
  if (await quoteTab.isVisible().catch(() => false)) {
    await quoteTab.click();
    await beat(page, 1200);
  }
  const priceInputs = page.locator('input[placeholder="0.00"]');
  const count = await priceInputs.count();
  for (let i = 0; i < count; i++) {
    const inp = priceInputs.nth(i);
    await inp.scrollIntoViewIfNeeded();
    await inp.fill(SAMPLE_PRICES[i % SAMPLE_PRICES.length]);
    await beat(page, 400);
  }
  const payment = page.locator('input[placeholder*="Net 30"]').first();
  if (await payment.isVisible().catch(() => false)) await payment.fill("Net-15");
  const delivery = page.locator('input[placeholder*="FOB"]').first();
  if (await delivery.isVisible().catch(() => false)) await delivery.fill("FOB Destination, 2-day delivery");
  await beat(page, 1000);

  const submit = page.getByRole("button", { name: /Submit Quote|Resubmit Quote/ });
  await submit.scrollIntoViewIfNeeded();
  await beat(page, 800);
  if (await submit.isEnabled().catch(() => false)) {
    const resp = page
      .waitForResponse((r) => /\/submit-quote$/.test(r.url()) && r.request().method() === "POST", {
        timeout: 30000,
      })
      .catch(() => {});
    await submit.click();
    await resp;
    await beat(page, 2500);
  }

  await caption(page, "AEROS", "Interactive agents on both sides of the deal.");
  await beat(page, 3000);
  await clearCaption(page);
});
