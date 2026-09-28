import { Link, useNavigate } from "react-router-dom";
import { logout } from "../../lib/api/auth";

export default function Navbar() {
  const navigate = useNavigate();
  const isLoggedIn = Boolean(localStorage.getItem("access"));

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }
  return (
    // <header> is the whole bar; border-b and border-line draws the header line
    <header className="bg-canvas">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-8 py-6">
        {/*This is the log for now */}
        {/* <a href="/" className="font-serif text-xl font-medium text-ink">
          GradPace
        </a> */}
        <Link to="/" className="text-xl font-bold">
          <span className="text-blue">Grad</span>
          <span className="text-pink">Pace</span>
        </Link>

        {/* Center nav links. gap-8 spaces the links, each link changes color only on hover */}
        <nav className="flex items-center gap-8 text-sm text-slate">
          <a
            href="#features"
            className="text-blue/70 transition-colors hover:text-blue"
          >
            Features
          </a>
          <a
            href="#how-it-works"
            className="text-blue/70 transition-colors hover:text-blue"
          >
            How it works
          </a>
          <a
            href="#about"
            className="text-blue/70 transition-colors hover:text-blue"
          >
            About
          </a>
        </nav>

        {/*Right side auth action. "Log in" and "Sign up" */}
        <div className="flex items-center gap-6">
          {isLoggedIn ? (
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md bg-blue px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue/90"
            >
              Log out
            </button>
          ) : (
            <>
              <Link
                to="/login"
                className="text-sm text-blue/70 transition-colors hover:text-blue"
              >
                Log in
              </Link>
              <Link
                to="/signup"
                className="rounded-md bg-blue px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue/90"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
