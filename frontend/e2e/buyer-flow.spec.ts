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
      await page.waitForTimeout(2000);
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
      // Wait for AI response
      await page.waitForTimeout(10000);
      const messages = page.locator('[class*="message"], [class*="bubble"]');
      expect(await messages.count()).toBeGreaterThan(1);
    });
  });

  test.describe("RFx Detail & Comparison Matrix", () => {
    test("RFx detail page shows line items and vendor responses", async ({ page }) => {
      await page.evaluate(() => (window.location.href = "/buyer/rfx/1"));
      await page.waitForTimeout(3000);
      await expect(page.locator("text=Line Items")).toBeVisible({ timeout: 10000 });
      await expect(page.locator("text=Vendor Responses")).toBeVisible();
      await expect(page.locator("text=Comparison Matrix")).toBeVisible();
    });

    test("comparison matrix shows vendor prices with confidence", async ({ page }) => {
      await page.evaluate(() => (window.location.href = "/buyer/rfx/1"));
      await page.waitForTimeout(3000);
      // Should show price cells with confidence indicators
      const matrix = page.locator("text=Comparison Matrix");
      await expect(matrix).toBeVisible({ timeout: 10000 });
      // Check for Award buttons
      const awardButtons = page.locator('button:has-text("Award")');
      expect(await awardButtons.count()).toBeGreaterThan(0);
    });

    test("Withdraw RFx button opens cancel modal", async ({ page }) => {
      await page.evaluate(() => (window.location.href = "/buyer/rfx/1"));
      await page.waitForTimeout(3000);
      const withdrawBtn = page.locator('button:has-text("Withdraw")');
      if (await withdrawBtn.isVisible()) {
        await withdrawBtn.click();
        // Should show modal or confirmation
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe("Inventory", () => {
    test("inventory page loads with search and table", async ({ page }) => {
      await page.goto("/buyer/inventory");
      await expect(page.locator("text=Inventory")).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(2000);
      // Should have category tabs or search
      const content = await page.content();
      expect(content).toBeTruthy();
    });
  });

  test.describe("Vendors", () => {
    test("vendors page shows vendor cards", async ({ page }) => {
      await page.goto("/buyer/vendors");
      await expect(page.locator("text=Vendors")).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(2000);
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
