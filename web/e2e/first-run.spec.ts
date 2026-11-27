import { expect, test } from "@playwright/test";

// Never send test traffic to the real error tracker.
test.beforeEach(async ({ page }) => {
  await page.route(/sentry\.io/, (route) => route.abort());
});

test("a new visitor taps dishes and gets something new, then makes it theirs", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("No sign-up, nothing to install")).toBeVisible();

  // The button guides until a dish is picked.
  const go = page.getByRole("button", { name: /tap a dish you make/i });
  await expect(go).toBeDisabled();

  const tiles = page.locator("button[aria-pressed]");
  for (const i of [0, 3, 8]) await tiles.nth(i).click();
  await page.getByRole("button", { name: /show me new dishes \(3\)/i }).click();

  // First visit leads with a new dish, written as changes.
  await expect(page.getByText("Something new, one step away")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/your .+, but…/).first()).toBeVisible();

  // Optional name, asked in place, kept on the device.
  await page.getByRole("button", { name: "What should I call you?" }).click();
  await page.getByPlaceholder("Your first name").fill("Asha");
  await page.getByRole("button", { name: "Save name" }).click();
  await expect(page.locator("h1").first()).toContainText("Asha.");

  // Theme choice survives a reload.
  await page.getByRole("button", { name: /kitchen/i }).last().click();
  await page.getByRole("button", { name: "Dark" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  // A returning visitor lands on their greeting, not the form.
  await page.getByRole("button", { name: /tonight/i }).last().click();
  await expect(page.locator("h1").first()).toContainText("Asha.");
});

test("the start screen guides the first tap and links the privacy page", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /tap a dish you make/i })).toBeDisabled();
  await expect(page.getByRole("link", { name: "Privacy" })).toBeVisible();
});
