export default function Navbar() {
  return (
    // <header> is the whole bar; border-b and border-line draws the header line
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-8 py-6">
        {/*This is the log for now */}
        <a href="/" className="font-serif text-xl font-medium text-ink">
          GradPace
        </a>

        {/* Center nav links. gap-8 spaces the links, each link changes color only on hover */}
        <nav className="flex items-center gap-8 text-sm text-slate">
          <a href="#features" className="transition-colors hover:text-ink">
            Features
          </a>
          <a href="#how-it-works" className="transition-colors hover:text-ink">
            How it works
          </a>
          <a href="#about" className="transition-colors hover:text-ink">
            About
          </a>
        </nav>

        {/*Right side auth action. "Log in" and "Sign up" */}
        <div className="flex items-center gap-6">
          <a
            href="/login"
            className="text-sm text-slate transition-colors hover:text-ink"
          >
            Log in
          </a>
          <a
            href="/signup"
            className="rounded-md bg-ink px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-pink"
          >
            Sign up
          </a>
        </div>
      </div>
    </header>
  );
}
