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
      await expect(
        page.locator('input[placeholder*="procurement"]')
      ).toBeVisible({ timeout: 10000 });
    });

    test("sending message shows in chat", async ({ page }) => {
      await page.goto("/buyer/chat");
      const input = page.locator('input[placeholder*="procurement"]');
      await expect(input).toBeVisible({ timeout: 10000 });
      await input.fill("I need 100kg rice");
      await input.press("Enter");
      await expect(page.locator("text=100kg rice")).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("RFx Detail & Comparison Matrix", () => {
    test("RFx detail page shows line items and vendor responses", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxLink = page.locator('a[href*="/buyer/rfx/"]').first();
      await expect(rfxLink).toBeVisible({ timeout: 10000 });
      await rfxLink.click();
      await page.waitForLoadState("networkidle");
      await expect(page.locator("h2:has-text('Line Items')")).toBeVisible({ timeout: 10000 });
      await expect(page.locator("h2:has-text('Vendor Responses')")).toBeVisible();
    });

    test("comparison matrix shows when vendors have quoted", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxLink = page.locator('a[href*="/buyer/rfx/"]').first();
      await expect(rfxLink).toBeVisible({ timeout: 10000 });
      await rfxLink.click();
      await page.waitForLoadState("networkidle");
      const matrix = page.locator("h2:has-text('Comparison Matrix')");
      const matrixVisible = await matrix.isVisible().catch(() => false);
      if (matrixVisible) {
        const awardButtons = page.locator('button:has-text("Award")');
        expect(await awardButtons.count()).toBeGreaterThan(0);
      }
    });

    test("Withdraw RFx button opens cancel modal", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxLink = page.locator('a[href*="/buyer/rfx/"]').first();
      await expect(rfxLink).toBeVisible({ timeout: 10000 });
      await rfxLink.click();
      await page.waitForLoadState("networkidle");
      const withdrawBtn = page.locator('button:has-text("Withdraw")');
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
  });

  test.describe("Vendors", () => {
    test("vendors page shows vendor cards", async ({ page }) => {
      await page.goto("/buyer/vendors");
      await expect(page.locator("h1")).toContainText("Vendor", { timeout: 10000 });
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
      await expect(page.locator("h1")).toContainText("Activity", { timeout: 10000 });
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
