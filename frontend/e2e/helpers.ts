import { type Page, expect } from "@playwright/test";

export async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  // Use evaluate to ensure click fires (Playwright sometimes misses React form submits)
  await page.evaluate(() => {
    const btn = document.querySelector('button[type="submit"]');
    if (btn) (btn as HTMLButtonElement).click();
  });
}

export async function loginAsBuyer(page: Page) {
  await login(page, "buyer@aeros.demo", "buyer123");
  await page.waitForURL("**/buyer/**", { timeout: 15000 });
}

export async function loginAsVendor(page: Page) {
  await login(page, "freshfarm@vendor.demo", "vendor123");
  await page.waitForURL("**/vendor/**", { timeout: 15000 });
}

export async function loginAsAdmin(page: Page) {
  await login(page, "admin@aeros.demo", "admin123");
  await page.waitForURL("**/admin/**", { timeout: 15000 });
}
