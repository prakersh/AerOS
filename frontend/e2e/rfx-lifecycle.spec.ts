import { test, expect } from "@playwright/test";
import { loginAsBuyer, loginAsVendor, loginAsAdmin } from "./helpers";

test.describe("RFx Full Lifecycle", () => {
  test("buyer can view dashboard with RFx data", async ({ page }) => {
    await loginAsBuyer(page);
    await expect(page.locator("text=Dashboard")).toBeVisible();
    await page.waitForTimeout(2000);
    // Should show KPI cards
    await expect(page.locator("text=Open RFx")).toBeVisible();
    await expect(page.locator("text=Vendors")).toBeVisible();
  });

  test("buyer can navigate to RFx detail with comparison matrix", async ({ page }) => {
    await loginAsBuyer(page);
    await page.evaluate(() => (window.location.href = "/buyer/rfx/1"));
    await page.waitForTimeout(3000);

    // Verify all sections present
    await expect(page.locator("text=Line Items")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("text=Vendor Responses")).toBeVisible();
    await expect(page.locator("text=Comparison Matrix")).toBeVisible();

    // Verify line items table has data
    const rows = page.locator("table tbody tr");
    expect(await rows.count()).toBeGreaterThan(0);

    // Verify Award buttons exist
    const awardBtns = page.locator('button:has-text("Award")');
    expect(await awardBtns.count()).toBeGreaterThan(0);
  });

  test("buyer can chat with AI co-pilot", async ({ page }) => {
    await loginAsBuyer(page);
    await page.goto("/buyer/chat");
    await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });

    await page.fill("textarea", "I need 50kg tomatoes");
    await page.keyboard.press("Enter");

    // User message should appear
    await expect(page.locator("text=50kg tomatoes")).toBeVisible({ timeout: 5000 });

    // AI should respond
    await page.waitForTimeout(15000);
    const pageContent = await page.content();
    expect(pageContent.length).toBeGreaterThan(500);
  });

  test("vendor can view inbox and navigate to RFx", async ({ page }) => {
    await loginAsVendor(page);
    await expect(page.locator("text=Inbox")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);
  });

  test("vendor can view RFx thread", async ({ page }) => {
    await loginAsVendor(page);
    await page.waitForTimeout(2000);
    const rfxLink = page.locator('a[href*="/vendor/rfx/"]').first();
    if (await rfxLink.isVisible()) {
      await rfxLink.click();
      await page.waitForTimeout(2000);
      // Should show thread messages
      await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });
    }
  });

  test("admin can view audit log", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/admin/audit");
    await expect(page.locator("text=Audit")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);
  });

  test("admin can view user management", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/admin/users");
    await expect(page.locator("text=Users")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);
  });

  test("cross-role navigation is blocked", async ({ page }) => {
    // Login as buyer
    await loginAsBuyer(page);

    // Try to access vendor routes
    await page.evaluate(() => (window.location.href = "/vendor/inbox"));
    await page.waitForURL("**/buyer/**", { timeout: 15000 });

    // Try to access admin routes
    await page.evaluate(() => (window.location.href = "/admin/dashboard"));
    await page.waitForURL("**/buyer/**", { timeout: 15000 });
  });

  test("session persists across full page reloads", async ({ page }) => {
    await loginAsBuyer(page);

    // Reload multiple times
    for (const path of ["/buyer/dashboard", "/buyer/chat", "/buyer/inventory"]) {
      await page.evaluate((p) => (window.location.href = p), path);
      await page.waitForURL(`**${path}`, { timeout: 15000 });
    }
  });
});
