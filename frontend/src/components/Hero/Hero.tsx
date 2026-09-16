import heroIllustration from "../../assets/hero-illustration.png";
/*
 * Homepage hero - headline, subhead, CTAs, and a graphic placeholder
 */
export default function Hero() {
  return (
    // grid-col-2 split the hero into two equal columns. the text with a button on the left
    // an illustration on the right
    // outer mx-auto max-w-6xl mirrors Navbar.tsx so both sections share the
    // same content width.
    <section className="mx-auto grid max-w-6xl grid-cols-2 items-center gap-16 px-8 py-28">
      <div className="max-w-md">
        {/* Header as an intro */}
        <h1 className="font-serif text-5xl font-medium leading-[1.1] text-ink">
          Your path from classroom to career, laid out clearly.
        </h1>

        <p className="mt-6 text-xl leading-relaxed text-slate">
          GradPace turns your coursework, projects, and goals into a
          personalized roadmap — so you know exactly where the gaps are, long
          before graduation.
        </p>

        <div className="mt-8 flex items-center gap-6">
          <a
            href="/signup"
            className="rounded-md bg-pink px-6 py-3 text-sm font-medium text-ink transition-colors hover:bg-pink/90"
          >
            Get started
          </a>
          <a
            href="/login"
            className="text-md text-slate transition-colors hover:text-ink"
          >
            Already have an account? Sign in
          </a>
        </div>
      </div>
      {/* This is where the hero image is located */}
      <img src={heroIllustration} alt="" className="h-auto w-full max-w-md" />
    </section>
  );
}
