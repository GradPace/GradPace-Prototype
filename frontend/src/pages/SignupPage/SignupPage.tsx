import Navbar from "../../components/Navbar/Navbar";
import { Link } from "react-router-dom";

export default function SignupPage() {
  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-10">
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

          <form className="mt-8 flex flex-col gap-6">
            <label className="flex flex-col gap-2 text-sm font-medium text-ink">
              Full name
              <input
                type="text"
                name="name"
                required
                className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
              />
            </label>

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
