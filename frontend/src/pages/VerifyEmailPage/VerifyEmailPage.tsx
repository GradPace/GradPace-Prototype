import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { ApiError, apiFetch } from "../../lib/api/api";

type Status =
  | "verifying"
  | "verified"
  | "already-verified"
  | "invalid"
  | "error";

// The page the emailed link opens: /verify-email?token=...
// It sends the token to /api/auth/verify-email/ (backend/accounts/urls.py),
// which marks the account verified.
export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<Status>(token ? "verifying" : "invalid");
  // Strict Mode runs effects twice in development - the link only needs
  // sending once.
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    apiFetch<{ verified: boolean; already_verified: boolean }>(
      "/api/auth/verify-email/",
      { token },
    )
      .then((result) =>
        setStatus(result.already_verified ? "already-verified" : "verified"),
      )
      .catch((err) =>
        // 400 means the link itself is bad or expired; anything else (the
        // server unreachable, say) is worth trying again.
        setStatus(err instanceof ApiError && err.status === 400 ? "invalid" : "error"),
      );
  }, [token]);

  const loggedIn = Boolean(localStorage.getItem("access"));

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />
      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-10">
          {status === "verifying" && (
            <>
              <h1 className="text-3xl font-medium text-ink">
                Verifying your email...
              </h1>
              <p className="mt-3 text-sm text-slate">One moment.</p>
            </>
          )}

          {status === "verified" && (
            <>
              <h1 className="text-3xl font-medium text-ink">
                Your email is verified
              </h1>
              <p className="mt-3 text-sm text-slate">
                Thanks - your email address is confirmed.
              </p>
            </>
          )}

          {status === "already-verified" && (
            <>
              <h1 className="text-3xl font-medium text-ink">
                Already verified
              </h1>
              <p className="mt-3 text-sm text-slate">
                This email address was already confirmed. You&apos;re all set.
              </p>
            </>
          )}

          {status === "invalid" && (
            <>
              <h1 className="text-3xl font-medium text-ink">
                This link doesn&apos;t work
              </h1>
              <p className="mt-3 text-sm text-slate">
                The verification link is invalid or has expired. Links work for
                7 days.
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <h1 className="text-3xl font-medium text-ink">
                Something went wrong
              </h1>
              <p className="mt-3 text-sm text-slate">
                We couldn&apos;t reach GradPace just now. Please try opening the
                link again in a moment.
              </p>
            </>
          )}

          {status !== "verifying" && (
            <Link
              to={loggedIn ? "/profile" : "/login"}
              className="mt-8 block w-full rounded-full bg-blue py-3 text-center text-sm font-semibold text-white transition-colors hover:opacity-90"
            >
              {loggedIn ? "Go to your profile" : "Log in"}
            </Link>
          )}
        </div>
      </main>
    </div>
  );
}
