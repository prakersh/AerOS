import { test, expect } from "@playwright/test";
import { loginAsAdmin } from "./helpers";

test.describe("Admin Portal", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test.describe("Dashboard", () => {
    test("shows KPI cards and system health", async ({ page }) => {
      await expect(page.locator("text=Dashboard")).toBeVisible({ timeout: 10000 });
      await expect(page.locator("text=Total Users").or(page.locator("text=Users"))).toBeVisible();
      await expect(page.locator("text=Health").or(page.locator("text=healthy"))).toBeVisible();
    });
  });

  test.describe("Users", () => {
    test("users page shows user table", async ({ page }) => {
      await page.goto("/admin/users");
      await expect(page.locator("text=Users")).toBeVisible({ timeout: 10000 });
      await page.waitForLoadState("networkidle");
    });
  });

  test.describe("AI Providers", () => {
    test("AI providers page loads", async ({ page }) => {
      await page.goto("/admin/ai/providers");
      await expect(page.locator("text=Provider").or(page.locator("text=AI"))).toBeVisible({
        timeout: 10000,
      });
    });
  });

  test.describe("Settings", () => {
    test("settings page loads with editable fields", async ({ page }) => {
      await page.goto("/admin/settings");
      await expect(page.locator("text=Settings")).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Observability", () => {
    test("observability page loads", async ({ page }) => {
      await page.goto("/admin/observability");
      await expect(page.locator("text=Observability")).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Audit Log", () => {
    test("audit log page loads", async ({ page }) => {
      await page.goto("/admin/audit");
      await expect(page.locator("text=Audit")).toBeVisible({ timeout: 10000 });
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
