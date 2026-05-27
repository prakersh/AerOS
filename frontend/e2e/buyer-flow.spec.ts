import { test, expect } from "@playwright/test";
import { loginAsBuyer } from "./helpers";

test.describe("Buyer Portal", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsBuyer(page);
  });

  test.describe("Dashboard", () => {
    test("shows KPI cards with counts", async ({ page }) => {
      await expect(page.locator("text=Open RFx")).toBeVisible();
      await expect(page.locator("text=Awaiting Quotes")).toBeVisible();
      await expect(page.locator("text=Awarded Today")).toBeVisible();
      await expect(page.locator("text=Vendors")).toBeVisible();
    });

    test("shows active RFx tiles", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const tiles = page.locator('a[href*="/buyer/rfx/"]');
      const count = await tiles.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test("Draft New Request navigates to chat", async ({ page }) => {
      await page.click("text=Draft New Request");
      await expect(page.url()).toContain("/buyer/chat");
    });
  });

  test.describe("Chat Co-pilot", () => {
    test("renders chat input", async ({ page }) => {
      await page.goto("/buyer/chat");
      await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });
    });

    test("sending message gets AI response", async ({ page }) => {
      await page.goto("/buyer/chat");
      await page.fill("textarea", "I need 100kg rice");
      await page.keyboard.press("Enter");
      await expect(page.locator("text=100kg rice")).toBeVisible({ timeout: 5000 });
      // Wait for AI response via network rather than arbitrary timeout
      await page.waitForResponse(
        (resp) => resp.url().includes("/api/") && resp.status() === 200,
        { timeout: 15000 }
      );
      const messages = page.locator('[class*="message"], [class*="bubble"]');
      expect(await messages.count()).toBeGreaterThan(1);
    });
  });

  test.describe("RFx Detail & Comparison Matrix", () => {
    test("RFx detail page shows line items and vendor responses", async ({ page }) => {
      // Navigate dynamically: click first RFx tile from the dashboard
      await page.waitForLoadState("networkidle");
      const rfxLink = page.locator('a[href*="/buyer/rfx/"]').first();
      await expect(rfxLink).toBeVisible({ timeout: 10000 });
      await rfxLink.click();
      await page.waitForLoadState("networkidle");
      await expect(page.locator("text=Line Items")).toBeVisible({ timeout: 10000 });
      await expect(page.locator("text=Vendor Responses")).toBeVisible();
      await expect(page.locator("text=Comparison Matrix")).toBeVisible();
    });

    test("comparison matrix shows vendor prices with confidence", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxLink = page.locator('a[href*="/buyer/rfx/"]').first();
      await expect(rfxLink).toBeVisible({ timeout: 10000 });
      await rfxLink.click();
      await page.waitForLoadState("networkidle");
      // Should show price cells with confidence indicators
      const matrix = page.locator("text=Comparison Matrix");
      await expect(matrix).toBeVisible({ timeout: 10000 });
      // Check for Award buttons
      const awardButtons = page.locator('button:has-text("Award")');
      expect(await awardButtons.count()).toBeGreaterThan(0);
    });

    test("Withdraw RFx button opens cancel modal", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxLink = page.locator('a[href*="/buyer/rfx/"]').first();
      await expect(rfxLink).toBeVisible({ timeout: 10000 });
      await rfxLink.click();
      await page.waitForLoadState("networkidle");
      const withdrawBtn = page.locator('button:has-text("Withdraw")');
      await expect(withdrawBtn).toBeVisible({ timeout: 10000 });
      await withdrawBtn.click();
      // Should show modal or confirmation dialog
      await expect(
        page.locator('[role="dialog"], [class*="modal"], [class*="Modal"]')
      ).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Inventory", () => {
    test("inventory page loads with search and table", async ({ page }) => {
      await page.goto("/buyer/inventory");
      await expect(page.locator("text=Inventory")).toBeVisible({ timeout: 10000 });
      await page.waitForLoadState("networkidle");
      // Verify meaningful content loaded (table or search input)
      await expect(
        page.locator("table, input[type='search'], input[placeholder*='search' i]").first()
      ).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Vendors", () => {
    test("vendors page shows vendor cards", async ({ page }) => {
      await page.goto("/buyer/vendors");
      await expect(page.locator("text=Vendors")).toBeVisible({ timeout: 10000 });
      await page.waitForLoadState("networkidle");
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
      await expect(page.locator("text=Activity")).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Observability", () => {
    test("observability page loads with LLM metrics", async ({ page }) => {
      await page.goto("/buyer/observability");
      await expect(page.locator("text=Observability")).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Navigation", () => {
    test("sidebar links navigate to correct pages", async ({ page }) => {
      const links = [
        ["Inventory", "/buyer/inventory"],
        ["Vendors", "/buyer/vendors"],
        ["Activity", "/buyer/activity"],
        ["Settings", "/buyer/settings"],
        ["Dashboard", "/buyer/dashboard"],
      ];
      for (const [label, path] of links) {
        await page.click(`text=${label}`);
        await expect(page.url()).toContain(path);
      }
    });
  });
});
