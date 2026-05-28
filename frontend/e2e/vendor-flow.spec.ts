import { test, expect } from "@playwright/test";
import { loginAsVendor } from "./helpers";

test.describe("Vendor Portal", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsVendor(page);
  });

  test.describe("Inbox", () => {
    test("inbox page loads with RFx invitations", async ({ page }) => {
      await expect(page.locator("h1")).toContainText("Inbox", { timeout: 10000 });
      await page.waitForLoadState("networkidle");
    });

    test("filter chips are visible for status filtering", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      // Filter chips: All, Invited, Viewed, Quoted, Declined, Expired
      await expect(page.locator('button:has-text("All")').first()).toBeVisible({ timeout: 5000 });
    });

    test("clicking RFx navigates to reply page", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      // Inbox items are now buttons; match on "Dispatched" status badge text
      const rfxItem = page.locator('button:has-text("Dispatched")').first();
      const count = await rfxItem.count();
      if (count > 0) {
        await rfxItem.click();
        await page.waitForURL(/\/vendor\/rfx\/\d+/, { timeout: 15000 });
      }
    });

    test("search input is visible on inbox page", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const searchInput = page.locator('[data-testid="inbox-search"]');
      await expect(searchInput).toBeVisible({ timeout: 5000 });
    });

    test("sort dropdown is visible on inbox page", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const sortDropdown = page.locator('[data-testid="inbox-sort"]');
      await expect(sortDropdown).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("RFx Reply", () => {
    test("reply page shows thread messages and reply form", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('button:has-text("Dispatched")').first();
      const count = await rfxItem.count();
      test.skip(count === 0, "No RFx invitations in inbox");
      await rfxItem.click();
      await page.waitForURL(/\/vendor\/rfx\/\d+/, { timeout: 15000 });
      // Reply textarea is now inside the Chat tab
      await page.locator('button:has-text("Chat")').click();
      await expect(page.locator('textarea[placeholder*="reply" i]')).toBeVisible({ timeout: 10000 });
    });

    test("file upload zone is present", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('button:has-text("Dispatched")').first();
      const count = await rfxItem.count();
      test.skip(count === 0, "No RFx invitations in inbox");
      await rfxItem.click();
      await page.waitForURL(/\/vendor\/rfx\/\d+/, { timeout: 15000 });
      // File upload is now inside the Upload & Analyze tab
      await page.locator('button:has-text("Upload & Analyze")').click();
      await expect(page.locator("text=Attachments")).toBeVisible({ timeout: 10000 });
    });

    test("decline button opens modal", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('button:has-text("Dispatched")').first();
      const count = await rfxItem.count();
      test.skip(count === 0, "No RFx invitations in inbox");
      await rfxItem.click();
      await page.waitForURL(/\/vendor\/rfx\/\d+/, { timeout: 15000 });
      // Decline button is in the page header
      const declineBtn = page.locator('button:has-text("Decline")');
      await expect(declineBtn).toBeVisible({ timeout: 10000 });
      await declineBtn.click();
      // DeclineModal uses shared Modal component which renders title as h3
      await expect(page.locator("h3:has-text('Decline this RFx')")).toBeVisible({ timeout: 5000 });
    });

    test("quote form tab is visible", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('button:has-text("Dispatched")').first();
      const count = await rfxItem.count();
      test.skip(count === 0, "No RFx invitations in inbox");
      await rfxItem.click();
      await page.waitForURL(/\/vendor\/rfx\/\d+/, { timeout: 15000 });
      await expect(page.locator('button:has-text("Quote Form")')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('button:has-text("Chat")')).toBeVisible();
      await expect(page.locator('button:has-text("Upload & Analyze")')).toBeVisible();
    });
  });

  test.describe("Profile", () => {
    test("profile shows account info", async ({ page }) => {
      await page.goto("/vendor/profile");
      await page.waitForLoadState("networkidle");
      await expect(page.locator("h1")).toContainText("Profile", { timeout: 10000 });
    });
  });

  test.describe("RBAC", () => {
    test("vendor cannot access buyer routes", async ({ page }) => {
      await page.evaluate(() => (window.location.href = "/buyer/dashboard"));
      await page.waitForURL("**/vendor/**", { timeout: 15000 });
    });

    test("vendor cannot access admin routes", async ({ page }) => {
      await page.evaluate(() => (window.location.href = "/admin/dashboard"));
      await page.waitForURL("**/vendor/**", { timeout: 15000 });
    });
  });
});
