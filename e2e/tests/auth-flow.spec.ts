import { expect, test, type Locator, type Page } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'

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

// Registering emails a verification link. In the e2e stack the backend writes
// every email it sends into backend/.e2e-mail (EMAIL_FILE_PATH in
// k8s/e2e/backend-pod.yaml; `make test-e2e` creates and clears the folder),
// so the test can open the same link a person would. `make test-e2e` runs
// from e2e/, hence the `..`.
const MAIL_DIR = path.resolve(process.cwd(), '..', 'backend', '.e2e-mail')

// Long lines in the email are quoted-printable: "=" is "=3D" and a line may
// be split with a trailing "=".
function decodeQuotedPrintable(text: string) {
  return text
    .replace(/=\r?\n/g, '')
    .replace(/=([0-9A-F]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)))
}

// The /verify-email?token=... link in each email sent to `email`, oldest first.
function emailedVerificationLinks(email: string): string[] {
  if (!existsSync(MAIL_DIR)) return []
  const addressed = new RegExp(`^To: .*${email.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'm')
  const links: string[] = []
  for (const file of readdirSync(MAIL_DIR).sort()) {
    // The file backend separates messages with a line of 79 dashes.
    for (const message of readFileSync(path.join(MAIL_DIR, file), 'utf8').split(/^-{79}$/m)) {
      if (!addressed.test(message)) continue
      const link = decodeQuotedPrintable(message).match(/\/verify-email\?token=[^\s"<>]+/)
      if (link) links.push(link[0])
    }
  }
  return links
}

// The nth (1-based) verification link emailed to `email`. The backend sends
// on a background thread, so give it a moment to arrive.
async function verificationLink(email: string, n = 1) {
  let links: string[] = []
  await expect
    .poll(() => (links = emailedVerificationLinks(email)).length, { timeout: 15_000 })
    .toBeGreaterThanOrEqual(n)
  return links[n - 1]
}

async function signUp(page: Page, first: string, last: string, email: string) {
  await page.goto('/signup')
  await page.getByLabel('First name').fill(first)
  await page.getByLabel('Last name').fill(last)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByLabel('Confirm password').fill(PASSWORD)
  await clickWhenEnabled(page.getByRole('button', { name: 'Sign up' }))
}

test.describe('signup -> verify email -> profile setup -> profile -> logout -> login', () => {
  test('completes the full cross-app journey', async ({ page }) => {
    const email = uniqueEmail()

    await signUp(page, 'Ada', 'Lovelace', email)

    // A new account is held on the verify page until its emailed link is opened.
    await expect(page).toHaveURL(/\/verify-your-email$/)
    await expect(page.getByRole('heading', { name: 'Verify your email' })).toBeVisible()
    await expect(page.getByText(email)).toBeVisible()

    await page.goto(await verificationLink(email))
    await expect(page.getByRole('heading', { name: 'Your email is verified' })).toBeVisible()
    await page.getByRole('link', { name: 'Go to your profile' }).click()

    // /profile sends an account with no profile yet on to profile setup.
    await expect(page).toHaveURL(/\/profileSetup$/)
    await expect(page.getByText(/hi ada, welcome to gradpace/i)).toBeVisible()

    await page.getByLabel('Student ID').fill(`S-${Date.now()}`)
    await page.getByLabel('University').selectOption('Old Dominion University')
    await page.getByLabel('Major').selectOption('Computer Science')
    await page.getByLabel('Location').fill('Norfolk, VA')
    await page.getByLabel('Target role').selectOption({ label: 'Software Developer' })
    await page.getByRole('button', { name: 'Create Profile' }).click()

    await expect(page).toHaveURL(/\/profile$/)
    await expect(
      page.getByRole('heading', { level: 2, name: 'Ada Lovelace' }),
    ).toBeVisible()
    await expect(page.getByRole('list').getByText('Old Dominion University')).toBeVisible()

    // Reload - confirms the JWT round-tripped through localStorage and the
    // backend still accepts it, not just that client-side routing worked.
    await page.reload()
    await expect(
      page.getByRole('heading', { level: 2, name: 'Ada Lovelace' }),
    ).toBeVisible()

    await page.getByRole('banner').getByRole('button', { name: 'Log out' }).click()
    await expect(page).toHaveURL(/\/login$/)

    await page.goto('/profile')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('holds an unverified account on the verify page until the link is opened', async ({
    page,
  }) => {
    const email = uniqueEmail()

    await signUp(page, 'Katherine', 'Johnson', email)
    await expect(page).toHaveURL(/\/verify-your-email$/)

    // The profile pages are out of reach, even by typing the address.
    await page.goto('/profile')
    await expect(page).toHaveURL(/\/verify-your-email$/)
    await page.goto('/profileSetup')
    await expect(page).toHaveURL(/\/verify-your-email$/)

    // "I've verified" before opening the link says so and stays.
    await page.getByRole('button', { name: /i.ve verified my email/i }).click()
    await expect(page.getByText(/not verified yet/i)).toBeVisible()
    await expect(page).toHaveURL(/\/verify-your-email$/)

    // Resend sends a second email, and that link works.
    await page.getByRole('button', { name: 'Resend the email' }).click()
    await expect(page.getByText(/sent a new link to/i)).toBeVisible()

    await page.goto(await verificationLink(email, 2))
    await expect(page.getByRole('heading', { name: 'Your email is verified' })).toBeVisible()

    // Opening the same link again is harmless.
    await page.goto(await verificationLink(email, 2))
    await expect(page.getByRole('heading', { name: 'Already verified' })).toBeVisible()

    await page.getByRole('link', { name: 'Go to your profile' }).click()
    await expect(page).toHaveURL(/\/profileSetup$/)
  })

  test('shows an error and stays on the page for a wrong password', async ({
    page,
  }) => {
    const email = uniqueEmail()

    // Register a real account first so the negative case below is a genuine
    // wrong-password rejection, not just "unknown user".
    await signUp(page, 'Grace', 'Hopper', email)
    await expect(page).toHaveURL(/\/verify-your-email$/)

    await page.getByRole('banner').getByRole('button', { name: 'Log out' }).click()
    await expect(page).toHaveURL(/\/login$/)

    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill('definitely-wrong-password')
    await clickWhenEnabled(page.getByRole('button', { name: 'Log in' }))

    await expect(page.getByText(/no active account found/i)).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })
})
