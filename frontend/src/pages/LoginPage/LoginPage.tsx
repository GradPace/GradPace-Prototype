// import { Link } from 'react-router-dom'
import Navbar from "../../components/Navbar/Navbar";
import { Link } from "react-router-dom";

/*
 * login page
 */
export default function LoginPage() {
  return (
    <div className="min-h-screen bg-paper font-sans text-ink">
      <Navbar />
      {/* main card that control its own width */}
      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-md rounded-2xl border border-line bg-white p-10 shadow-lg">
          <h1 className="font-serif text-4xl font-medium text-ink">Log in</h1>
          <p className="mt-3 text-sm text-slate">
            New to GradPace?{" "}
            <Link
              to="/signup"
              className="text-ink underline underline-offset-2 hover:text-pink"
            >
              Create an account
            </Link>
          </p>

          <form className="mt-8 flex flex-col gap-6">
            <label className="flex flex-col gap-2 text-sm font-medium text-ink">
              Email
              <input
                type="email"
                name="email"
                required
                className="rounded-md border border-line px-4 py-3 text-base text-ink outline-none focus:border-ink"
              />
            </label>

            <label className="flex flex-col gap-2 text-sm font-medium text-ink">
              Password
              <input
                type="password"
                name="password"
                required
                className="rounded-md border border-line px-4 py-3 text-base text-ink outline-none focus:border-ink"
              />
            </label>

            <button
              type="submit"
              className="mt-2 w-full rounded-full bg-pink py-3 text-sm font-semibold text-ink transition-colors hover:bg-pink/90"
            >
              Log in
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
