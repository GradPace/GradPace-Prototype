import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { ApiError, apiFetch, apiGet } from "../../lib/api/api";
import {
  canSkipVerification,
  knownMe,
  rememberMe,
  type Me,
} from "../../lib/api/me";

// Where a new account lands until its email is verified: tells the user to
// open the link that was emailed, and can send it again. Verified users who
// open it are sent on.
export default function CheckEmailPage() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(knownMe());
  const [loggedOut, setLoggedOut] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<Me>("/api/auth/me/")
      .then((latest) => {
        rememberMe(latest);
        setMe(latest);
        if (canSkipVerification(latest)) navigate("/profile", { replace: true });
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) setLoggedOut(true);
        else setError("We couldn't load your account. Please refresh the page.");
      });
  }, [navigate]);

  async function resend() {
    setNotice(null);
    setError(null);
    setBusy(true);
    try {
      const result = await apiFetch<{ sent: boolean; already_verified: boolean }>(
        "/api/auth/verify-email/resend/",
        {},
        true,
      );
      if (result.already_verified) {
        navigate("/profile", { replace: true });
      } else {
        setNotice(`We sent a new link to ${me?.email}.`);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not send the email. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function checkAgain() {
    setNotice(null);
    setError(null);
    setBusy(true);
    try {
      const latest = await apiGet<Me>("/api/auth/me/");
      setMe(latest);
      if (canSkipVerification(latest)) {
        navigate("/profile", { replace: true });
      } else {
        setNotice(
          "Not verified yet. Open the link in the email we sent you, then try again.",
        );
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not check your account.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loggedOut) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />
      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-10">
          <h1 className="text-4xl font-medium text-ink">Verify your email</h1>
          {me ? (
            <p className="mt-3 text-sm text-slate">
              We sent a link to <span className="text-ink">{me.email}</span>.
              Open it to confirm your email address, then come back here to
              continue. If you don&apos;t see it, check your spam folder.
            </p>
          ) : (
            <p className="mt-3 text-sm text-slate">Loading...</p>
          )}

          {notice && <p className="mt-6 text-sm text-ink">{notice}</p>}
          {error && <p className="mt-6 text-sm text-pink">{error}</p>}

          {me && (
            <div className="mt-8 flex flex-col gap-3">
              <button
                type="button"
                onClick={checkAgain}
                disabled={busy}
                className="w-full rounded-full bg-blue py-3 text-sm font-semibold text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                I&apos;ve verified my email
              </button>
              <button
                type="button"
                onClick={resend}
                disabled={busy}
                className="w-full rounded-full border border-line py-3 text-sm font-semibold text-ink transition-colors hover:border-blue disabled:cursor-not-allowed disabled:opacity-60"
              >
                Resend the email
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
