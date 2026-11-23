import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { apiFetch } from "../../lib/api/api";

// Asks for the email address and has the backend send a reset link
// (/api/auth/password/reset/). The link opens /reset-password.
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const address = String(new FormData(event.currentTarget).get("email") ?? "");
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch("/api/auth/password/reset/", { email: address });
      setEmail(address);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not send the email. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />
      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-10">
          {email === null ? (
            <>
              <h1 className="text-4xl font-medium text-ink">
                Forgot your password?
              </h1>
              <p className="mt-3 text-sm text-slate">
                Enter your email and we&apos;ll send you a link to choose a new
                one.
              </p>
              <form
                className="mt-8 flex flex-col gap-6"
                onSubmit={handleSubmit}
              >
                <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                  Email
                  <input
                    type="email"
                    name="email"
                    required
                    className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                  />
                </label>
                {error && <p className="text-sm text-pink">{error}</p>}
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full rounded-full bg-blue py-3 text-sm font-semibold text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Send reset link
                </button>
              </form>
              <p className="mt-6 text-sm text-slate">
                Remembered it?{" "}
                <Link
                  to="/login"
                  className="text-ink underline underline-offset-2 hover:text-pink"
                >
                  Log in
                </Link>
              </p>
            </>
          ) : (
            <>
              <h1 className="text-3xl font-medium text-ink">Check your email</h1>
              {/* The same message whether or not the address has an account,
                  like the backend's response, so this form can't be used to
                  find out who is registered. */}
              <p className="mt-3 text-sm text-slate">
                If an account exists for {email}, we&apos;ve sent a link to reset
                your password. The link works for 10 minutes. If it doesn&apos;t
                arrive, check your spam folder.
              </p>
              <Link
                to="/login"
                className="mt-8 block w-full rounded-full bg-blue py-3 text-center text-sm font-semibold text-white transition-colors hover:opacity-90"
              >
                Back to log in
              </Link>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
