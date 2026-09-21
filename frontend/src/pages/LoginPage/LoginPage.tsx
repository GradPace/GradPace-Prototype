import { useState, type FormEvent } from "react";
import Navbar from "../../components/Navbar/Navbar";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../lib/api/api";

/*
 * login page
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const { access, refresh } = await apiFetch("/api/auth/login/", {
        email: form.get("email"),
        password: form.get("password"),
      });
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      navigate("/");
    } catch {
      setError("Invalid email or password.");
    }
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

            {error && <p className="mt-2 text-sm text-pink">{error}</p>}

            <button
              type="submit"
              className="mt-2 w-full rounded-full bg-blue py-3 text-sm font-semibold text-white transition-colors hover:bg-blue/90"
            >
              Log in
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
