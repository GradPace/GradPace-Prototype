import Navbar from "../../components/Navbar/Navbar";
import { useNavigate } from "react-router-dom";
import { logout } from "../../lib/api/auth";
import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api/api";

export default function ProfileSetupPage() {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState<string | null>(null);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  useEffect(() => {
    apiGet<{ first_name: string }>("/api/auth/me")
      .then((user) => setFirstName(user.first_name))
      .catch(() => setFirstName(null));
  });
  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-xl rounded-2xl border border-line bg-surface p-10">
          <h1 className="text-4xl font-medium text-ink">
            Hi{firstName ? ` ${firstName}` : ""}, welcome to GradPace
          </h1>
          <h2 className="mt-2 text-xl font-medium text-slate">
            Tell us a little more about you.
          </h2>
          <p className="mt-3 text-sm text-slate">
            Want to finish setting up later?{" "}
            <button
              type="button"
              onClick={handleLogout}
              className="text-ink hover:text-pink"
            >
              Log out
            </button>
          </p>

          <form className="mt-8 flex flex-col gap-6">
            <div className="grid gap-4">
              <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                Student ID
                <input
                  type="text"
                  name="student_id"
                  required
                  className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                Major
                <input
                  type="text"
                  name="major"
                  required
                  className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                University
                <input
                  type="text"
                  name="uni"
                  required
                  className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                Location
                <input
                  type="text"
                  name="location"
                  className="rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue"
                />
              </label>

              <label className="flex items-center gap-2 text-sm font-medium text-ink">
                <input
                  type="checkbox"
                  name="graduated"
                  className="h-4 w-4 rounded border-line accent-blue"
                />
                I have already graduated
              </label>

              <button
                type="submit"
                className="mt-2 w-full rounded-full bg-blue py-3 text-sm font-semibold text-white transition-colors hover:bg-blue/90"
              >
                Create Profile
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
