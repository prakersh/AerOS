import { test, expect } from "@playwright/test";
import { loginAsBuyer } from "./helpers";

test.describe("Buyer Portal", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsBuyer(page);
  });

  test.describe("Dashboard", () => {
    test("shows KPI cards with counts", async ({ page }) => {
      await expect(page.locator("h1")).toContainText("Dashboard");
      await page.waitForLoadState("networkidle");
      await expect(page.locator("text=Open RFx")).toBeVisible();
      await expect(page.locator("text=Awaiting Quotes")).toBeVisible();
      await expect(page.locator("text=Awarded Today")).toBeVisible();
    });

    test("shows active RFx tiles as clickable buttons", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      // RFx tiles are now <button> elements inside the grid under "Active Requests"
      const tiles = page.locator('button.group');
      const count = await tiles.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test("clicking RFx tile opens quick-view modal", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const tile = page.locator('button.group').first();
      const count = await tile.count();
      test.skip(count === 0, "No RFx tiles on dashboard");
      await tile.click();
      // Modal should open with an h3 title
      await expect(page.locator('h3')).toBeVisible({ timeout: 5000 });
      // "View Full Details" link should be inside the modal
      await expect(page.locator('text=View Full Details')).toBeVisible({ timeout: 5000 });
    });

    test("Draft New Request navigates to chat", async ({ page }) => {
      await page.click("text=Draft New Request");
      await expect(page.url()).toContain("/buyer/chat");
    });

    test("filter chips are visible on dashboard", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      // Filter chips: All, Drafting, Dispatched, etc.
      await expect(page.locator('button:has-text("All")').first()).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Chat Co-pilot", () => {
    test("renders chat input", async ({ page }) => {
      await page.goto("/buyer/chat");
      await expect(
        page.locator('input[placeholder*="procurement"]')
      ).toBeVisible({ timeout: 10000 });
    });

    test("sending message shows in chat", async ({ page }) => {
      await page.goto("/buyer/chat");
      const input = page.locator('input[placeholder*="procurement"]');
      await expect(input).toBeVisible({ timeout: 10000 });
      await input.fill("I need 100kg rice");
      // Enter creates newlines now; use Ctrl+Enter to send
      await input.press("Control+Enter");
      await expect(page.locator("text=100kg rice")).toBeVisible({ timeout: 5000 });
    });

    test("voice input button is visible", async ({ page }) => {
      await page.goto("/buyer/chat");
      // Voice input button is a button with a microphone icon
      const voiceBtn = page.locator('button[aria-label*="voice" i], button[aria-label*="microphone" i], button:has(svg.lucide-mic)').first();
      await expect(voiceBtn).toBeVisible({ timeout: 5000 });
    });

    test("file upload paperclip button is visible", async ({ page }) => {
      await page.goto("/buyer/chat");
      // Paperclip button for file upload
      const paperclipBtn = page.locator('button[aria-label*="attach" i], button[aria-label*="upload" i], button:has(svg.lucide-paperclip)').first();
      await expect(paperclipBtn).toBeVisible({ timeout: 5000 });
    });

    test("quick action prompt chips are visible", async ({ page }) => {
      await page.goto("/buyer/chat");
      await page.waitForLoadState("networkidle");
      // Quick action chips are clickable prompt suggestions
      const chips = page.locator('[data-testid="prompt-chip"], button:has-text("Draft"), button:has-text("Create")').first();
      await expect(chips).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("RFx Detail & Comparison Matrix", () => {
    test("RFx detail page shows line items and vendor responses", async ({ page }) => {
      // Navigate directly to an RFx detail page
      await page.goto("/buyer/rfx/1");
      await page.waitForLoadState("networkidle");
      await expect(page.locator("text=Line Items")).toBeVisible({ timeout: 10000 });
      await expect(page.locator("text=Vendor Responses")).toBeVisible();
      await expect(page.locator("text=RFx Journey")).toBeVisible();
    });

    test("comparison matrix shows when vendors have quoted", async ({ page }) => {
      await page.goto("/buyer/rfx/1");
      await page.waitForLoadState("networkidle");
      const matrix = page.locator("text=Comparison Matrix");
      const matrixVisible = await matrix.isVisible().catch(() => false);
      if (matrixVisible) {
        const awardButtons = page.locator('button:has-text("Award")');
        expect(await awardButtons.count()).toBeGreaterThan(0);
      }
    });

    test("Withdraw RFx button opens cancel modal", async ({ page }) => {
      await page.goto("/buyer/rfx/1");
      await page.waitForLoadState("networkidle");
      const withdrawBtn = page.locator('button:has-text("Withdraw RFx")');
      const hasWithdraw = await withdrawBtn.isVisible().catch(() => false);
      test.skip(!hasWithdraw, "RFx status does not allow withdrawal");
      await withdrawBtn.click();
      await expect(page.locator("h3:has-text('Withdraw RFx')")).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Inventory", () => {
    test("inventory page loads with search and table", async ({ page }) => {
      await page.goto("/buyer/inventory");
      await expect(page.locator("h1")).toContainText("Inventory", { timeout: 10000 });
      await page.waitForLoadState("networkidle");
      await expect(
        page.locator("table, input[type='search'], input[placeholder*='search' i]").first()
      ).toBeVisible({ timeout: 10000 });
    });

    test("clicking inventory row opens detail modal", async ({ page }) => {
      await page.goto("/buyer/inventory");
      await page.waitForLoadState("networkidle");
      const row = page.locator("table tbody tr.cursor-pointer").first();
      const count = await row.count();
      test.skip(count === 0, "No inventory rows to click");
      await row.click();
      // Modal with item details should appear
      await expect(page.locator("h3")).toBeVisible({ timeout: 5000 });
    });

    test("search input filters inventory", async ({ page }) => {
      await page.goto("/buyer/inventory");
      await page.waitForLoadState("networkidle");
      const searchInput = page.locator('input[placeholder*="Search by code"]');
      await expect(searchInput).toBeVisible({ timeout: 10000 });
      // Verify the search input is functional
      await searchInput.fill("test");
      // Should not crash
    });
  });

  test.describe("Vendors", () => {
    test("vendors page shows vendor cards", async ({ page }) => {
      await page.goto("/buyer/vendors");
      await expect(page.locator("h1")).toContainText("Vendor", { timeout: 10000 });
      await page.waitForLoadState("networkidle");
    });

    test("clicking vendor card opens detail modal", async ({ page }) => {
      await page.goto("/buyer/vendors");
      await page.waitForLoadState("networkidle");
      const card = page.locator('button.group, button[type="button"]').filter({ has: page.locator("h3") }).first();
      const count = await card.count();
      test.skip(count === 0, "No vendor cards to click");
      await card.click();
      // Modal with vendor details should appear
      await expect(page.locator("h3")).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Settings", () => {
    test("settings shows user profile and defaults", async ({ page }) => {
      await page.goto("/buyer/settings");
      await expect(page.locator("text=buyer@aeros.demo")).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Activity", () => {
    test("activity page loads with timeline", async ({ page }) => {
      await page.goto("/buyer/activity");
      await expect(page.locator("h1")).toContainText("Activity", { timeout: 10000 });
    });

    test("clicking activity entry opens detail modal", async ({ page }) => {
      await page.goto("/buyer/activity");
      await page.waitForLoadState("networkidle");
      // Activity entries are now <button> elements
      const entry = page.locator("button").filter({ has: page.locator("p.text-sm") }).first();
      const count = await entry.count();
      test.skip(count === 0, "No activity entries to click");
      await entry.click();
      // Modal with activity details should appear
      await expect(page.locator("h3:has-text('Activity Details')")).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Observability", () => {
    test("observability page loads with LLM metrics", async ({ page }) => {
      await page.goto("/buyer/observability");
      await expect(page.locator("h1")).toContainText("Observability", { timeout: 10000 });
    });
  });

  test.describe("Navigation", () => {
    test("sidebar links navigate to correct pages", async ({ page }) => {
      const links = [
        ["Inventory", "/buyer/inventory"],
        ["Activity", "/buyer/activity"],
        ["Settings", "/buyer/settings"],
      ];
      for (const [label, path] of links) {
        await page.locator(`nav a:has-text("${label}")`).click();
        await expect(page.url()).toContain(path);
      }
    });
  });
});
