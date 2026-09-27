import Navbar from "../../components/Navbar/Navbar";
import { Link } from "react-router-dom";

export default function ProfileSetupPage() {
  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-xl rounded-2xl border border-line bg-surface p-10">
          <h1 className="text-4xl font-medium text-ink">
            Tell us a little more about you.
          </h1>
          <p className="mt-3 text-sm text-slate">
            Want to finish setting up later?{" "}
            <Link to="/login" className="text-ink hover:text-pink">
              Log out
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
