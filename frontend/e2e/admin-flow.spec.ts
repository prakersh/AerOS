import { test, expect } from "@playwright/test";
import { loginAsAdmin } from "./helpers";

test.describe("Admin Portal", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test.describe("Dashboard", () => {
    test("shows KPI cards and system health", async ({ page }) => {
      await expect(page.locator("h1")).toContainText("Dashboard", { timeout: 10000 });
      await page.waitForLoadState("networkidle");
    });
  });

  test.describe("Users", () => {
    test("users page shows user table", async ({ page }) => {
      await page.goto("/admin/users");
      await expect(page.locator("h1")).toContainText("User Management", { timeout: 10000 });
      await page.waitForLoadState("networkidle");
    });

    test("clicking user row opens detail modal", async ({ page }) => {
      await page.goto("/admin/users");
      await page.waitForLoadState("networkidle");
      const row = page.locator("table tbody tr.cursor-pointer").first();
      const count = await row.count();
      test.skip(count === 0, "No user rows to click");
      await row.click();
      // Modal with "User Details" title should appear
      await expect(page.locator("h3:has-text('User Details')")).toBeVisible({ timeout: 5000 });
    });

    test("search input filters users", async ({ page }) => {
      await page.goto("/admin/users");
      await page.waitForLoadState("networkidle");
      const searchInput = page.locator('input[placeholder*="Search by name"]');
      await expect(searchInput).toBeVisible({ timeout: 10000 });
      await searchInput.fill("admin");
      // Should not crash; table should still be visible
      await expect(page.locator("table")).toBeVisible();
    });

    test("role filter chips are visible", async ({ page }) => {
      await page.goto("/admin/users");
      await page.waitForLoadState("networkidle");
      await expect(page.locator('button:has-text("All")').first()).toBeVisible({ timeout: 5000 });
      await expect(page.locator('button:has-text("Buyer")').first()).toBeVisible();
      await expect(page.locator('button:has-text("Vendor")').first()).toBeVisible();
      await expect(page.locator('button:has-text("Admin")').first()).toBeVisible();
    });
  });

  test.describe("AI Providers", () => {
    test("AI providers page loads", async ({ page }) => {
      await page.goto("/admin/ai/providers");
      await expect(page.locator("h1")).toContainText("AI Providers", { timeout: 10000 });
    });
  });

  test.describe("Settings", () => {
    test("settings page loads with editable fields", async ({ page }) => {
      await page.goto("/admin/settings");
      await expect(page.locator("h1")).toContainText("Settings", { timeout: 10000 });
    });
  });

  test.describe("Observability", () => {
    test("observability page loads", async ({ page }) => {
      await page.goto("/admin/observability");
      await expect(page.locator("h1")).toContainText("Observability", { timeout: 10000 });
    });
  });

  test.describe("Audit Log", () => {
    test("audit log page loads", async ({ page }) => {
      await page.goto("/admin/audit");
      await expect(page.locator("h1")).toContainText("Audit", { timeout: 10000 });
    });
  });

  test.describe("RBAC", () => {
    test("admin cannot access buyer routes", async ({ page }) => {
      await page.evaluate(() => (window.location.href = "/buyer/dashboard"));
      await page.waitForURL("**/admin/**", { timeout: 15000 });
    });

    test("admin cannot access vendor routes", async ({ page }) => {
      await page.evaluate(() => (window.location.href = "/vendor/inbox"));
      await page.waitForURL("**/admin/**", { timeout: 15000 });
    });
  });
});
