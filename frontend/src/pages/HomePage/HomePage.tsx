import Hero from "../../components/Hero/Hero";
import Navbar from "../../components/Navbar/Navbar";

/**
 * GradPace — Home page
 * Sections built so far: Navbar, Hero (headline + subhead graphic placeholder).
 * Thin composition layer only — content lives in the
 * section components themselves, so this file just decides page order.
 */
export default function HomePage() {
  return (
    <div className="min-h-screen bg-paper font-sans text-ink">
      <Navbar />
      <Hero />
    </div>
  );
}
