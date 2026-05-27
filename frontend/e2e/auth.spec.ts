import { test, expect } from "@playwright/test";
import { login, loginAsBuyer, loginAsVendor, loginAsAdmin } from "./helpers";

test.describe("Authentication", () => {
  test("login page renders AEROS branding and form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("h1")).toContainText("AEROS");
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText("Sign in");
  });

  test("register link navigates to register page", async ({ page }) => {
    await page.goto("/login");
    await page.click("text=Register");
    await expect(page.url()).toContain("/register");
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "bad@email.com");
    await page.fill('input[type="password"]', "wrongpass");
    await page.evaluate(() => {
      const btn = document.querySelector('button[type="submit"]');
      if (btn) (btn as HTMLButtonElement).click();
    });
    await expect(page.locator("text=Invalid credentials")).toBeVisible({ timeout: 10000 });
  });

  test("login as buyer redirects to buyer dashboard", async ({ page }) => {
    await loginAsBuyer(page);
    await expect(page.url()).toContain("/buyer/dashboard");
    await expect(page.locator("text=Dashboard")).toBeVisible();
  });

  test("login as vendor redirects to vendor inbox", async ({ page }) => {
    await loginAsVendor(page);
    await expect(page.url()).toContain("/vendor/inbox");
  });

  test("login as admin redirects to admin dashboard", async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.url()).toContain("/admin/dashboard");
  });

  test("unauthenticated user redirected to login from buyer route", async ({ page }) => {
    await page.goto("/buyer/dashboard");
    await page.waitForURL("**/login", { timeout: 15000 });
    await expect(page.url()).toContain("/login");
  });

  test("unauthenticated user redirected to login from vendor route", async ({ page }) => {
    await page.goto("/vendor/inbox");
    await page.waitForURL("**/login", { timeout: 15000 });
    await expect(page.url()).toContain("/login");
  });

  test("unauthenticated user redirected to login from admin route", async ({ page }) => {
    await page.goto("/admin/dashboard");
    await page.waitForURL("**/login", { timeout: 15000 });
    await expect(page.url()).toContain("/login");
  });

  test("authenticated buyer visiting login is redirected to dashboard", async ({ page }) => {
    await loginAsBuyer(page);
    await page.goto("/login");
    await page.waitForURL("**/buyer/dashboard", { timeout: 15000 });
  });

  test("logout clears session and redirects to login", async ({ page }) => {
    await loginAsBuyer(page);
    await page.click("text=Sign out");
    await page.waitForURL("**/login", { timeout: 10000 });
  });

  test("full page reload preserves session", async ({ page }) => {
    await loginAsBuyer(page);
    await page.evaluate(() => (window.location.href = "/buyer/dashboard"));
    await page.waitForURL("**/buyer/dashboard", { timeout: 15000 });
    await expect(page.locator("text=Dashboard")).toBeVisible();
  });
});
