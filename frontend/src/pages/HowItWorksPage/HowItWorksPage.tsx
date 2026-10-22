import Navbar from "../../components/Navbar/Navbar";

type Step = {
  title: string;
  items: string[];
};

const STEPS: Step[] = [
  {
    title: "Build Your Profile",
    items: [
      "Secure account creation and login",
      "Enter coursework, skills, projects, and experience",
      "Upload your unofficial transcript to update your skills automatically",
    ],
  },
  {
    title: "Plan Your Path",
    items: [
      "Personalized career roadmap",
      "Roadmap dashboard to track your progress",
      "Early-warning gap detection",
      "Industry readiness benchmarking",
    ],
  },
  {
    title: "Find Opportunities",
    items: [
      "Guided recommendations for your next steps",
      "Local internship and networking event recommendations",
      "Notifications for new recommendations and gaps",
      "Alumni insights that keep guidance current",
    ],
  },
];

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto max-w-6xl px-8 pt-8 pb-24">
        <header className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-semibold text-ink">How it works</h1>
          <p className="mt-4 text-base text-slate">
            GradPace takes you from where you are today to where you want to be
            after graduation, in three steps.
          </p>
        </header>

        <ol className="mt-14 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="flex flex-col rounded-2xl border border-line bg-surface p-8"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-blue/15 text-sm font-semibold text-blue">
                {index + 1}
              </span>
              <h2 className="mt-5 text-xl font-semibold text-ink">
                {step.title}
              </h2>
              <ul className="mt-5 flex flex-col gap-3">
                {step.items.map((item) => (
                  <li key={item} className="flex gap-3 text-sm text-slate">
                    <span
                      className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-pink"
                      aria-hidden="true"
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>

        {/* <div className="mt-14 text-center">
          <Link
            to="/signup"
            className="inline-block rounded-full bg-blue px-8 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue/90"
          >
            Get started
          </Link>
        </div> */}
      </main>
    </div>
  );
}
