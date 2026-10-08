import { expect, test, type Locator } from '@playwright/test'
import { randomUUID } from 'node:crypto'

// The dev backend's db.sqlite3 is a persisted file, not an in-memory test
// DB, and `make test-e2e` reuses it across every test in the run (it's only
// wiped before/after the whole suite, not per test) - so every test that
// registers a user needs a unique email, the same reason
// accounts/factories.py's UserFactory uses sequential emails on the backend
// side.
function uniqueEmail() {
  return `e2e-${Date.now()}-${randomUUID()}@example.com`
}

// Non-dictionary, matches the style of accounts/factories.py's
// UserFactory DEFAULT_PASSWORD so it passes the same validators
// (accounts/validators.py) without looking like a guessable word.
const PASSWORD = 'Zq9!wPbn3'

// Sign up / Log in stay disabled until the Turnstile widget passes (dev uses
// Cloudflare's always-pass test key, ~1-2s). Wait for that before clicking:
// clicking a disabled button makes Playwright retry, and its retries scroll
// the page - right after a scroll Chromium can route the click into the
// Turnstile iframe instead of the button, so the form never submits.
async function clickWhenEnabled(button: Locator) {
  await expect(button).toBeEnabled({ timeout: 15_000 })
  await button.click()
}

test.describe('signup -> profile setup -> profile -> logout -> login', () => {
  test('completes the full cross-app journey', async ({ page }) => {
    const email = uniqueEmail()

    await page.goto('/signup')
    await page.getByLabel('First name').fill('Ada')
    await page.getByLabel('Last name').fill('Lovelace')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByLabel('Confirm password').fill(PASSWORD)
    await clickWhenEnabled(page.getByRole('button', { name: 'Sign up' }))

    await expect(page).toHaveURL(/\/profileSetup$/)
    await expect(page.getByText(/hi ada, welcome to gradpace/i)).toBeVisible()

    await page.getByLabel('Student ID').fill(`S-${Date.now()}`)
    await page.getByLabel('University').fill('State University')
    await page.getByLabel('Major').fill('Computer Science')
    await page.getByLabel('Location').fill('Remote')
    await page.getByRole('button', { name: 'Create Profile' }).click()

    await expect(page).toHaveURL(/\/profile$/)
    await expect(page.getByText('Ada Lovelace')).toBeVisible()
    await expect(page.getByText('State University')).toBeVisible()

    // Reload - confirms the JWT round-tripped through localStorage and the
    // backend still accepts it, not just that client-side routing worked.
    await page.reload()
    await expect(page.getByText('Ada Lovelace')).toBeVisible()

    await page.getByRole('banner').getByRole('button', { name: 'Log out' }).click()
    await expect(page).toHaveURL(/\/login$/)

    await page.goto('/profile')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('shows an error and stays on the page for a wrong password', async ({
    page,
  }) => {
    const email = uniqueEmail()

    // Register a real account first so the negative case below is a genuine
    // wrong-password rejection, not just "unknown user".
    await page.goto('/signup')
    await page.getByLabel('First name').fill('Grace')
    await page.getByLabel('Last name').fill('Hopper')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByLabel('Confirm password').fill(PASSWORD)
    await clickWhenEnabled(page.getByRole('button', { name: 'Sign up' }))
    await expect(page).toHaveURL(/\/profileSetup$/)

    // ProfileSetupPage has two "Log out" controls - the Navbar's and its own
    // inline one - scope to the Navbar so the locator isn't ambiguous.
    await page.getByRole('banner').getByRole('button', { name: 'Log out' }).click()
    await expect(page).toHaveURL(/\/login$/)

    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill('definitely-wrong-password')
    await clickWhenEnabled(page.getByRole('button', { name: 'Log in' }))

    await expect(page.getByText(/no active account found/i)).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })
})
