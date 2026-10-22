import heroIllustration from "../../assets/hero-illustration.webp";
import { Link } from "react-router-dom";

/*
 * Homepage hero - headline, subhead, CTAs, and a graphic placeholder
 */
export default function Hero() {
  const isLoggedIn = Boolean(localStorage.getItem("access"));
  return (
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
          {isLoggedIn ? (
            <Link
              to="/profile"
              className="rounded-md bg-blue px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue/90"
            >
              Go to your profile
            </Link>
          ) : (
            <>
              <Link
                to="/signup"
                className="rounded-md bg-blue px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue/90"
              >
                Get started
              </Link>
              <Link
                to="/login"
                className="text-sm text-slate transition-colors hover:text-pink"
              >
                Already have an account? Sign in
              </Link>
            </>
          )}
        </div>
      </div>
      <img
        src={heroIllustration}
        // srcSet={`${heroIllustration512} 512w, ${heroIllustration1024} 1024w`}
        sizes="(min-width: 1024px) 448px, 50vw"
        width={1024}
        height={1024}
        fetchPriority="high"
        alt=""
        className="h-auto w-full max-w-md"
      />
    </section>
  );
}
