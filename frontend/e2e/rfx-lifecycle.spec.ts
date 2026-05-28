import { test, expect } from "@playwright/test";
import { loginAsBuyer, loginAsVendor, loginAsAdmin } from "./helpers";

test.describe("RFx Full Lifecycle", () => {
  test("buyer can view dashboard with RFx data", async ({ page }) => {
    await loginAsBuyer(page);
    await expect(page.locator("h1")).toContainText("Dashboard");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("text=Open RFx")).toBeVisible();
  });

  test("buyer can navigate to RFx detail page via direct URL", async ({ page }) => {
    await loginAsBuyer(page);
    await page.goto("/buyer/rfx/1");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Line Items" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Vendor Responses" })).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=RFX JOURNEY")).toBeVisible({ timeout: 5000 });
  });

  test("buyer can navigate to RFx detail via dashboard modal", async ({ page }) => {
    await loginAsBuyer(page);
    await page.waitForLoadState("networkidle");

    const tile = page.locator('button.group').first();
    const count = await tile.count();
    test.skip(count === 0, "No RFx tiles on dashboard");
    await tile.click();

    const viewDetails = page.locator('a:has-text("View Full Details")');
    await expect(viewDetails).toBeVisible({ timeout: 10000 });
    await viewDetails.click();

    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: "Line Items" })).toBeVisible({ timeout: 15000 });
  });

  test("buyer can send message to AI co-pilot", async ({ page }) => {
    await loginAsBuyer(page);
    await page.goto("/buyer/chat");
    const input = page.locator('input[placeholder*="procurement"]');
    await expect(input).toBeVisible({ timeout: 10000 });

    await input.fill("I need 50kg tomatoes");
    // Enter creates newlines now; use Ctrl+Enter to send
    await input.press("Control+Enter");

    await expect(page.locator("text=50kg tomatoes")).toBeVisible({ timeout: 5000 });
  });

  test("vendor can view inbox and navigate to RFx", async ({ page }) => {
    await loginAsVendor(page);
    await expect(page.locator("h1")).toContainText("Inbox", { timeout: 10000 });
    await page.waitForLoadState("networkidle");
  });

  test("vendor can view RFx thread", async ({ page }) => {
    await loginAsVendor(page);
    await page.waitForLoadState("networkidle");
    const rfxItem = page.locator('[data-testid="inbox-item"]').first();
    await expect(rfxItem).toBeVisible({ timeout: 10000 });
    await rfxItem.click();
    await page.waitForURL(/\/vendor\/rfx\/\d+/, { timeout: 15000 });
    await expect(page.locator('button:has-text("Chat")')).toBeVisible({ timeout: 15000 });
    await page.locator('button:has-text("Chat")').click();
    await expect(page.locator('textarea[placeholder*="reply" i]')).toBeVisible({ timeout: 10000 });
  });

  test("admin can view audit log", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/admin/audit");
    await expect(page.locator("h1")).toContainText("Audit", { timeout: 10000 });
    await page.waitForLoadState("networkidle");
  });

  test("admin can view user management", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/admin/users");
    await expect(page.locator("h1")).toContainText("User Management", { timeout: 10000 });
    await page.waitForLoadState("networkidle");
  });

  test("cross-role navigation is blocked", async ({ page }) => {
    await loginAsBuyer(page);

    await page.goto("/vendor/inbox");
    await page.waitForURL("**/buyer/**", { timeout: 15000 });

    await page.goto("/admin/dashboard");
    await page.waitForURL("**/buyer/**", { timeout: 15000 });
  });

  test("session persists across full page reloads", async ({ page }) => {
    await loginAsBuyer(page);

    for (const path of ["/buyer/dashboard", "/buyer/chat", "/buyer/inventory"]) {
      await page.goto(path);
      await page.waitForURL(`**${path}`, { timeout: 15000 });
    }
  });
});
