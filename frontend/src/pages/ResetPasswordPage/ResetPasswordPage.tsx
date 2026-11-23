import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import PasswordRules from "../../components/PasswordRules/PasswordRules";
import { apiFetch } from "../../lib/api/api";

// The page the emailed reset link opens: /reset-password?uid=...&token=...
// It sends the new password with those two values to
// /api/auth/password/reset/confirm/ (backend/accounts/urls.py).
export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const uid = params.get("uid");
  const token = params.get("token");
  const [error, setError] = useState<string | null>(null);
  const [showPasswordHint, setShowPasswordHint] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch("/api/auth/password/reset/confirm/", {
        uid,
        token,
        new_password: form.get("new_password"),
        new_password_confirm: form.get("new_password_confirm"),
      });
      // The backend signs out every session when the password changes, so
      // drop any login left in this browser - otherwise the login page would
      // send the user straight back to a profile that no longer loads.
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      setDone(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not reset your password. Please try again.",
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
          {done ? (
            <>
              <h1 className="text-3xl font-medium text-ink">
                Your password has been changed
              </h1>
              <p className="mt-3 text-sm text-slate">
                You can log in with your new password now.
              </p>
              <Link
                to="/login"
                className="mt-8 block w-full rounded-full bg-blue py-3 text-center text-sm font-semibold text-white transition-colors hover:opacity-90"
              >
                Log in
              </Link>
            </>
          ) : !uid || !token ? (
            <>
              <h1 className="text-3xl font-medium text-ink">
                This link doesn&apos;t work
              </h1>
              <p className="mt-3 text-sm text-slate">
                The reset link is incomplete. Open the link from your email
                again, or ask for a new one.
              </p>
              <Link
                to="/forgot-password"
                className="mt-8 block w-full rounded-full bg-blue py-3 text-center text-sm font-semibold text-white transition-colors hover:opacity-90"
              >
                Get a new link
              </Link>
            </>
          ) : (
            <>
              <h1 className="text-4xl font-medium text-ink">
                Choose a new password
              </h1>
              <form
                className="mt-8 flex flex-col gap-6"
                onSubmit={handleSubmit}
              >
                <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                  New password
                  <input
                    type="password"
                    name="new_password"
                    required
                    onFocus={() => setShowPasswordHint(true)}
                    onBlur={() => setShowPasswordHint(false)}
                    className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                  />
                </label>
                {showPasswordHint && <PasswordRules />}
                <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                  Confirm new password
                  <input
                    type="password"
                    name="new_password_confirm"
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
                  Change password
                </button>
              </form>
              <p className="mt-6 text-sm text-slate">
                Link expired?{" "}
                <Link
                  to="/forgot-password"
                  className="text-ink underline underline-offset-2 hover:text-pink"
                >
                  Get a new one
                </Link>
              </p>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
