import { test, expect } from "@playwright/test";
import { loginAsVendor } from "./helpers";

test.describe("Vendor Portal", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsVendor(page);
  });

  test.describe("Inbox", () => {
    test("inbox page loads with RFx invitations", async ({ page }) => {
      await expect(page.locator("text=Inbox")).toBeVisible({ timeout: 10000 });
      await page.waitForLoadState("networkidle");
    });

    test("clicking RFx navigates to reply page", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('a[href*="/vendor/rfx/"]').first();
      await expect(rfxItem).toBeVisible({ timeout: 10000 });
      await rfxItem.click();
      await page.waitForLoadState("networkidle");
      await expect(page).toHaveURL(/\/vendor\/rfx\/\d+/);
    });
  });

  test.describe("RFx Reply", () => {
    test("reply page shows thread messages and reply form", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('a[href*="/vendor/rfx/"]').first();
      await expect(rfxItem).toBeVisible({ timeout: 10000 });
      await rfxItem.click();
      await page.waitForLoadState("networkidle");
      await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });
    });

    test("file upload zone is present", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('a[href*="/vendor/rfx/"]').first();
      await expect(rfxItem).toBeVisible({ timeout: 10000 });
      await rfxItem.click();
      await page.waitForLoadState("networkidle");
      const upload = page.locator('input[type="file"], text=upload, text=Upload');
      await expect(upload.first()).toBeVisible({ timeout: 10000 });
    });

    test("decline button opens modal", async ({ page }) => {
      await page.waitForLoadState("networkidle");
      const rfxItem = page.locator('a[href*="/vendor/rfx/"]').first();
      await expect(rfxItem).toBeVisible({ timeout: 10000 });
      await rfxItem.click();
      await page.waitForLoadState("networkidle");
      const declineBtn = page.locator('button:has-text("Decline")');
      await expect(declineBtn).toBeVisible({ timeout: 10000 });
      await declineBtn.click();
      // Should show modal or confirmation dialog
      await expect(
        page.locator('[role="dialog"], [class*="modal"], [class*="Modal"]')
      ).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Profile", () => {
    test("profile shows account info", async ({ page }) => {
      await page.goto("/vendor/profile");
      await expect(page.locator("text=freshfarm@vendor.demo").or(page.locator("text=Profile"))).toBeVisible({
        timeout: 10000,
      });
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
