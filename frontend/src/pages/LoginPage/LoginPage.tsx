import { useState, type FormEvent } from "react";
import Navbar from "../../components/Navbar/Navbar";
import { Navigate } from "react-router-dom";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { ApiError, apiFetch, apiGet } from "../../lib/api/api";
import Turnstile from "../../components/Turnstile/Turnstile";

/*
 * login page
 * Access token- when frontend wants to access something that requires the user to be logged in (60 min)
 * Refresh token - used to get a new access token when the old access token expires (7 days)
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  // Turnstile token - submit stays disabled until the challenge passes.
  // Bumping turnstileKey remounts the widget for a fresh (single-use) token.
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [turnstileKey, setTurnstileKey] = useState(0);

  // This function job is, on click to take the username and password input and send it
  // to /api/auth/login/ (located @ backend/accounts/urls.py) to see if it's correct
  // if not generate an error message
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); // prevents the browser from reloading
    const form = new FormData(event.currentTarget);
    try {
      const { access, refresh } = await apiFetch<{
        access: string;
        refresh: string;
      }>("/api/auth/login/", {
        email: form.get("email"),
        password: form.get("password"),
        cf_turnstile_response: turnstileToken,
      });
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
    } catch (err) {
      // The token was used up by this attempt - get a new one.
      setTurnstileToken(null);
      setTurnstileKey((key) => key + 1);
      // A network-level failure (CORS block, backend unreachable) throws a
      // plain Error too ("Failed to fetch"), not just ApiError - err.message
      // covers both instead of only showing validation errors.
      setError(
        err instanceof Error ? err.message : "Invalid email or password.",
      );
      return;
    }

    // here will determin where the user gets send based on if they finished setting up their profile
    try {
      await apiGet("/api/auth/profile/");
      navigate("/profile", { replace: true }); // profile exists
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        navigate("/profileSetup", { replace: true }); //signed up but never finished profile setup
      } else {
        navigate("/", { replace: true });
      }
    }
  }

  if (localStorage.getItem("access")) {
    return <Navigate to="/profile" replace />;
  }

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />
      {/* main card that control its own width */}
      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-10">
          <h1 className="text-4xl font-medium text-ink">Log in</h1>
          <p className="mt-3 text-sm text-slate">
            New to GradPace?{" "}
            <Link
              to="/signup"
              className="text-ink underline underline-offset-2 hover:text-pink"
            >
              Create an account
            </Link>
          </p>

          <form className="mt-8 flex flex-col gap-6" onSubmit={handleSubmit}>
            <label className="flex flex-col gap-2 text-sm font-medium text-ink">
              Email
              <input
                type="email"
                name="email"
                required
                className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-medium text-ink">
              Password
              <input
                type="password"
                name="password"
                required
                className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
              />
            </label>

            <Turnstile
              key={turnstileKey}
              action="login"
              onToken={setTurnstileToken}
            />

            {error && <p className="mt-2 text-sm text-pink">{error}</p>}

            <button
              type="submit"
              disabled={!turnstileToken}
              className="mt-2 w-full rounded-full bg-blue py-3 text-sm font-semibold text-white transition-colors hover:bg-blue/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Log in
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
