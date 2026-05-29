import { test, type Page } from "@playwright/test";
import { login } from "../helpers";
import { beat, titleCard, waitForCopilotReply, nav, scrollThrough } from "./demo-helpers";

const BUYER = "buyer@aeros.demo";
const ATT = (name: string) => `../demo/attachments/${name}`;

const CREATE_PROMPT =
  "I need 200kg tomatoes, 150kg onions, 300 litres of full cream milk and 50kg paneer by tomorrow morning. Please create the request.";
const DISPATCH_PROMPT = "Send this request to all the matching vendors.";

async function loginAs(page: Page, email: string, portal: "buyer" | "vendor") {
  await page.context().clearCookies();
  await login(page, email, email === BUYER ? "buyer123" : "vendor123");
  await page.waitForURL(`**/${portal}/**`, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await beat(page, 1500);
}

async function openRfxAsVendor(page: Page, rfxId: string) {
  await page.goto("/vendor/inbox");
  await page.waitForLoadState("networkidle");
  await beat(page, 1800);
  const item = page.locator('[data-testid="inbox-item"]').filter({ hasText: "Procurement" }).first();
  if (await item.isVisible().catch(() => false)) {
    await item.click();
  } else {
    await page.goto(`/vendor/rfx/${rfxId}`);
  }
  await page.waitForLoadState("networkidle");
  await beat(page, 1800);
}

async function vendorUploadAndAnalyze(page: Page, file: string) {
  await page.getByRole("button", { name: "Upload & Analyze" }).click();
  await beat(page, 1200);
  await page.locator('input[type="file"]').first().setInputFiles(ATT(file));
  await page.waitForLoadState("networkidle").catch(() => {});
  await beat(page, 2200);
  const askBtn = page.getByRole("button", { name: /Ask AI about this document/i }).first();
  await askBtn.waitFor({ state: "visible", timeout: 30000 });
  await beat(page, 1200);
  const resp = page
    .waitForResponse(
      (r) => /\/api\/chat$/.test(new URL(r.url()).pathname) && r.request().method() === "POST",
      { timeout: 90000 },
    )
    .catch(() => {});
  await askBtn.click();
  await resp;
  await page.waitForLoadState("networkidle").catch(() => {});
  await beat(page, 2000);
  const panel = page.locator("text=Vendor Co-pilot").first();
  if (await panel.isVisible().catch(() => false)) await panel.scrollIntoViewIfNeeded();
  await beat(page, 3500);
}

async function vendorFillAndSubmit(page: Page, prices: string[], payment: string, delivery: string) {
  await page.getByRole("button", { name: "Quote Form" }).click();
  await beat(page, 1200);
  const priceInputs = page.locator('input[placeholder="0.00"]');
  const count = await priceInputs.count();
  for (let i = 0; i < count; i++) {
    const inp = priceInputs.nth(i);
    await inp.scrollIntoViewIfNeeded();
    await inp.fill(prices[i % prices.length]);
    await beat(page, 450);
  }
  const pay = page.locator('input[placeholder*="Net 30"]').first();
  if (await pay.isVisible().catch(() => false)) await pay.fill(payment);
  const del = page.locator('input[placeholder*="FOB"]').first();
  if (await del.isVisible().catch(() => false)) await del.fill(delivery);
  await beat(page, 1200);
  const submit = page.getByRole("button", { name: /Submit Quote|Resubmit Quote/ });
  await submit.scrollIntoViewIfNeeded();
  await beat(page, 800);
  if (await submit.isEnabled().catch(() => false)) {
    const resp = page
      .waitForResponse(
        (r) => /\/submit-quote$/.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 30000 },
      )
      .catch(() => {});
    await submit.click();
    await resp;
    await beat(page, 2500);
  }
}

test("AEROS complete walkthrough — buyer drafts, vendors reply, buyer awards", async ({ page }) => {
  test.setTimeout(600000);
  let rfxId = "";

  // ── Intro ──
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await titleCard(page, {
    step: "AEROS",
    actor: "AI Procurement OS",
    text: "From a plain-language request to awarded vendors — end to end",
    accent: "#a5b4fc",
  }, 3800);

  // ── Step 1: Buyer logs in ──
  await titleCard(page, {
    step: "Step 1 · Buyer",
    actor: "Buyer",
    account: BUYER,
    text: "Sign in to the buyer portal",
  });
  await loginAs(page, BUYER, "buyer");
  await beat(page, 2000);
  await scrollThrough(page, 900, 4);
  await nav(page, "Vendors", "/buyer/vendors");
  await scrollThrough(page, 1000, 5);

  // ── Step 2: Buyer drafts an RFx by chat ──
  await titleCard(page, {
    step: "Step 2 · Buyer",
    actor: "Buyer",
    account: BUYER,
    text: "Describe the need in plain language — the co-pilot drafts the request",
  });
  await nav(page, "Chat Co-pilot", "/buyer/chat");
  const clearBtn = page.getByRole("button", { name: "Clear chat" });
  if (await clearBtn.isVisible().catch(() => false)) {
    await clearBtn.click();
    await beat(page, 800);
  }
  const input = page.locator('input[placeholder*="procurement"]');
  await input.waitFor({ state: "visible", timeout: 15000 });
  await beat(page, 1200);
  await input.click();
  await input.fill(CREATE_PROMPT);
  await beat(page, 1000);
  await input.press("Enter");
  await waitForCopilotReply(page, 3000);
  // Show the drafted request + its line-item details table.
  await scrollThrough(page, 1300, 6);
  await beat(page, 2500);

  // ── Step 3: Buyer dispatches to matching vendors ──
  await titleCard(page, {
    step: "Step 3 · Buyer",
    actor: "Buyer",
    account: BUYER,
    text: "Send the RFx — the agent invites the matching vendors automatically",
  });
  await input.click();
  await input.fill(DISPATCH_PROMPT);
  await beat(page, 1000);
  await input.press("Enter");
  await waitForCopilotReply(page, 3000);
  await scrollThrough(page, 1100, 5);
  await beat(page, 1500);

  // Open the dispatched request to show the vendor lanes.
  const openBtn = page.getByRole("button", { name: /Open request/i }).last();
  if (await openBtn.isVisible().catch(() => false)) {
    await openBtn.scrollIntoViewIfNeeded();
    await beat(page, 1000);
    await openBtn.click();
    await page.waitForLoadState("networkidle").catch(() => {});
  }
  await page.waitForURL("**/buyer/rfx/**", { timeout: 15000 }).catch(() => {});
  const m = page.url().match(/\/buyer\/rfx\/(\d+)/);
  if (m) rfxId = m[1];
  await beat(page, 2500);
  await scrollThrough(page, 1800, 8);

  // ── Step 4: Vendor replies by uploading a spreadsheet ──
  await titleCard(page, {
    step: "Step 4 · Vendor",
    actor: "Vendor — Sabzi Mandi",
    account: "sabzi@vendor.demo",
    text: "Reply in any format — upload a quote and let AI read it",
    accent: "#34d399",
  });
  await loginAs(page, "sabzi@vendor.demo", "vendor");
  await openRfxAsVendor(page, rfxId);
  await vendorUploadAndAnalyze(page, "sabzimandi_quote.xlsx");
  await vendorFillAndSubmit(page, ["15.00", "18.50", "55.00", "305.00"], "Net-30", "Next-day mandi dispatch");

  // ── Step 5: A second vendor replies with a scanned photo (vision) ──
  await titleCard(page, {
    step: "Step 5 · Vendor",
    actor: "Vendor — FreshFarm Dairy",
    account: "freshfarm@vendor.demo",
    text: "Another vendor replies with a scanned photo — read by the vision model",
    accent: "#34d399",
  });
  await loginAs(page, "freshfarm@vendor.demo", "vendor");
  await openRfxAsVendor(page, rfxId);
  await vendorUploadAndAnalyze(page, "scanned_proforma.jpg");
  await vendorFillAndSubmit(page, ["16.50", "20.00", "52.00", "290.00"], "NET15", "Doorstep, 18 hours");

  // ── Step 6: Buyer compares and awards ──
  await titleCard(page, {
    step: "Step 6 · Buyer",
    actor: "Buyer",
    account: BUYER,
    text: "Compare the offers side-by-side and split the award across vendors",
  });
  await loginAs(page, BUYER, "buyer");
  await page.goto(`/buyer/rfx/${rfxId}`);
  await page.waitForLoadState("networkidle");
  await beat(page, 2500);
  await scrollThrough(page, 2000, 9);

  // Award two line items (split across vendors where possible).
  const compSection = page.locator("section").filter({ hasText: "Comparison Matrix" });
  const rows = compSection.locator("tbody tr");
  const rowCount = await rows.count().catch(() => 0);
  for (let r = 0; r < Math.min(rowCount, 2); r++) {
    // Prefer the lowest-price "Best Price" cell when present.
    const best = rows.nth(r).getByRole("button", { name: /^Award$/ });
    const btn = best.first();
    if (await btn.isVisible().catch(() => false)) {
      await btn.scrollIntoViewIfNeeded();
      await beat(page, 900);
      await btn.click();
      await beat(page, 1000);
    }
  }
  const awardSelected = page.getByRole("button", { name: /Award Selected/ });
  if (await awardSelected.isVisible().catch(() => false)) {
    await awardSelected.scrollIntoViewIfNeeded();
    await beat(page, 1800);
    await awardSelected.click();
    await beat(page, 1200);
    const confirm = page.getByRole("button", { name: /Confirm Award/ });
    if (await confirm.isVisible().catch(() => false)) {
      await confirm.click();
      await page.waitForLoadState("networkidle").catch(() => {});
      await beat(page, 2500);
    }
  }
  await scrollThrough(page, 1000, 4);

  // ── Outro ──
  await titleCard(page, {
    step: "AEROS",
    actor: "AI Procurement OS",
    text: "Drafted, dispatched, quoted, compared, awarded — one continuous flow",
    accent: "#a5b4fc",
  }, 4000);
});
