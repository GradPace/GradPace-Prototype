import { useState, type CSSProperties } from "react";
import Navbar from "../../components/Navbar/Navbar";

const FEATURES = [
  "Academic and professional profile input",
  "Personalized career roadmap",
  "Roadmap dashboard with progress tracking",
  "Early-warning gap detection",
  "Industry readiness benchmarking",
  "Guided recommendations for next steps",
  "Alumni survey insights that keep guidance current",
];

// Signed distance from the current card, wrapping around both ends.
// With 7 cards this is -3..3, so the card before the first is the last one.
function offsetFrom(index: number, current: number, total: number): number {
  let offset = (index - current + total) % total;
  if (offset > total / 2) offset -= total;
  return offset;
}

// Cover Flow look: center card flat and in front, neighbours smaller,
// dimmed and turned in toward the center, everything else hidden.
function cardStyle(offset: number): CSSProperties {
  const base = "translate(-50%, -50%)";

  if (offset === 0) {
    return { transform: `${base} scale(1)`, opacity: 1, zIndex: 30 };
  }

  const side = Math.sign(offset);
  if (Math.abs(offset) === 1) {
    return {
      transform: `${base} translateX(${side * 75}%) scale(0.8) rotateY(${-side * 35}deg)`,
      opacity: 0.6,
      zIndex: 20,
    };
  }

  // Parked just off to the side so they slide in instead of popping in
  return {
    transform: `${base} translateX(${side * 130}%) scale(0.6) rotateY(${-side * 45}deg)`,
    opacity: 0,
    zIndex: 10,
    pointerEvents: "none",
  };
}

export default function FeaturesPage() {
  const [current, setCurrent] = useState(0);
  const total = FEATURES.length;

  // Wraps around: Next on the last card goes back to the first
  function goTo(index: number) {
    setCurrent((index + total) % total);
  }

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto max-w-5xl px-8 pt-8 pb-24">
        <header className="text-center">
          <h1 className="text-4xl font-semibold text-ink">Features</h1>
          <p className="mt-4 text-base text-slate">
            Everything GradPace gives you on the way from classroom to career.
          </p>
        </header>

        <section
          className="mt-14"
          aria-roledescription="carousel"
          aria-label="GradPace features"
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") goTo(current + 1);
            if (event.key === "ArrowLeft") goTo(current - 1);
          }}
        >
          {/* Stage - perspective gives the side cards their 3D tilt */}
          <div
            className="relative h-80 overflow-hidden"
            style={{ perspective: "1000px" }}
          >
            {FEATURES.map((title, index) => {
              const offset = offsetFrom(index, current, total);
              const visible = Math.abs(offset) <= 1;

              return (
                <button
                  key={title}
                  type="button"
                  onClick={() => goTo(index)}
                  tabIndex={visible ? 0 : -1}
                  aria-hidden={!visible}
                  aria-current={offset === 0}
                  className="absolute top-1/2 left-1/2 flex h-56 w-64 items-center justify-center rounded-2xl border border-line bg-surface p-8 text-center shadow-lg transition-all duration-500 ease-out motion-reduce:transition-none sm:w-80"
                  style={cardStyle(offset)}
                >
                  <span className="text-xl leading-snug font-bold text-ink">
                    {title}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Controls */}
          <div className="mt-8 flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={() => goTo(current - 1)}
              className="rounded-md border border-line px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:border-blue hover:text-blue"
            >
              Previous
            </button>

            <div className="flex items-center gap-2">
              {FEATURES.map((title, index) => (
                <button
                  key={title}
                  type="button"
                  onClick={() => goTo(index)}
                  aria-label={`Show ${title}`}
                  aria-current={index === current}
                  className={`h-2 rounded-full transition-all ${
                    index === current
                      ? "w-6 bg-blue"
                      : "w-2 bg-line hover:bg-slate"
                  }`}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={() => goTo(current + 1)}
              className="rounded-md bg-blue px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue/90"
            >
              Next
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
