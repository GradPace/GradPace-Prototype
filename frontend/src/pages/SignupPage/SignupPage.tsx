import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../lib/api/api";
import Navbar from "../../components/Navbar/Navbar";
import { Link } from "react-router-dom";

export default function SignupPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [showPasswordHint, setShowPasswordHint] = useState(false);

  // This function job is, on click to take the inputs and send it
  // to /api/auth/register/ (located @ backend/accounts/urls.py)
  // to store the registration form.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const { access, refresh } = await apiFetch<{
        access: string;
        refresh: string;
      }>("/api/auth/register/", {
        first_name: form.get("first_name"),
        last_name: form.get("last_name"),
        email: form.get("email"),
        password: form.get("password"),
        password_confirm: form.get("password_confirm"),
      });
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      navigate("/profileSetup", { replace: true });
    } catch (err) {
      // A network-level failure (CORS block, backend unreachable) throws a
      // plain Error too ("Failed to fetch"), not just ApiError - err.message
      // covers both instead of only showing validation errors.
      setError(
        err instanceof Error
          ? err.message
          : "Could not create account. Check your details and try again.",
      );
    }
  }

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-xl rounded-2xl border border-line bg-surface p-10">
          <h1 className="text-4xl font-medium text-ink">Create your account</h1>
          <p className="mt-3 text-sm text-slate">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-ink underline underline-offset-2 hover:text-pink"
            >
              Log in
            </Link>
          </p>

          <form className="mt-8 flex flex-col gap-6" onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                First name
                <input
                  type="text"
                  name="first_name"
                  required
                  className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                Last name
                <input
                  type="text"
                  name="last_name"
                  required
                  className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                />
              </label>
            </div>

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
                onFocus={() => setShowPasswordHint(true)}
                onBlur={() => setShowPasswordHint(false)}
                className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
              />
            </label>

            {showPasswordHint && (
              <ul className="-mt-4 list-disc space-y-1 pl-5 text-sm text-slate">
                <li>At least 8 characters</li>
                <li>1 uppercase letter</li>
                <li>1 number</li>
                <li>1 special character (!@#$%^&*)</li>
                <li>Not a common word or common password</li>
                <li>
                  No repeated or sequential characters (e.g. "aaaa", "1234")
                </li>
              </ul>
            )}

            <label className="flex flex-col gap-2 text-sm font-medium text-ink">
              Confirm password
              <input
                type="password"
                name="password_confirm"
                required
                className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
              />
            </label>

            {error && <p className="mt-2 text-sm text-pink">{error}</p>}

            <button
              type="submit"
              className="mt-2 w-full rounded-full bg-blue py-3 text-sm font-semibold text-white transition-colors hover:bg-blue/90"
            >
              Sign up
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
