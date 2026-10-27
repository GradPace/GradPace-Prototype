import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { ApiError, apiGet } from "../../lib/api/api";

// GET /api/benchmark/demo/me/ - only the parts this page uses
type SkillGroupResult = {
  key: string;
  name: string;
  points: number;
  out_of: number;
  best_tool: string | null; // label of the tool that earned the points
  level: string | null; // Learning / Practicing / Project ready
  options: { name: string; label: string }[];
};

type NextStep = {
  kind: "skill" | "course";
  name: string;
  points_available: number;
};

type DemoReadiness = {
  overall_readiness_score: number;
  skills: { groups: SkillGroupResult[] };
  courses: {
    list: { code: string; name: string; taken: boolean; points: number }[];
  };
  certificates: {
    bonus: number;
    max_bonus: number;
    counted: string[];
    options: string[];
  };
  next_steps: NextStep[];
};

type Resource = { name: string; url: string };

// Free places to learn each skill group, shown while a student is still
// Learning (or hasn't started) a group
const RESOURCES: Record<string, Resource[]> = {
  fundamentals: [
    { name: "freeCodeCamp", url: "https://www.freecodecamp.org/learn" },
    { name: "Harvard CS50", url: "https://cs50.harvard.edu/x/" },
  ],
  language: [
    { name: "freeCodeCamp", url: "https://www.freecodecamp.org/learn" },
    { name: "The Odin Project", url: "https://www.theodinproject.com/" },
  ],
  version_control: [
    { name: "GitHub Skills", url: "https://skills.github.com/" },
    { name: "Learn Git Branching", url: "https://learngitbranching.js.org/" },
  ],
  databases: [
    { name: "SQLBolt", url: "https://sqlbolt.com/" },
    { name: "freeCodeCamp", url: "https://www.freecodecamp.org/learn" },
  ],
  backend: [
    { name: "freeCodeCamp", url: "https://www.freecodecamp.org/learn" },
    { name: "The Odin Project", url: "https://www.theodinproject.com/" },
  ],
  frontend: [
    { name: "React docs", url: "https://react.dev/learn" },
    { name: "freeCodeCamp", url: "https://www.freecodecamp.org/learn" },
  ],
  cloud: [
    { name: "AWS Skill Builder", url: "https://skillbuilder.aws/" },
    { name: "Microsoft Learn", url: "https://learn.microsoft.com/training/" },
  ],
  devops: [
    { name: "Docker: Get started", url: "https://docs.docker.com/get-started/" },
  ],
  os: [{ name: "Linux Journey", url: "https://linuxjourney.com/" }],
  problem_solving: [{ name: "LeetCode", url: "https://leetcode.com/" }],
};

function points(value: number): string {
  return `+${value.toFixed(1)} pts`;
}

export default function Feedback() {
  const navigate = useNavigate();
  const [readiness, setReadiness] = useState<DemoReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<DemoReadiness>("/api/benchmark/demo/me/")
      .then(setReadiness)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { replace: true }); // not logged in / token expired
        } else if (err instanceof ApiError && err.status === 404 && !err.data) {
          navigate("/profileSetup", { replace: true }); // no profile yet
        } else {
          setError("Could not load your feedback.");
        }
      });
  }, [navigate]);

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto max-w-4xl px-8 pt-2 pb-24">
        {error && <p className="text-sm text-pink">{error}</p>}
        {!readiness && !error && (
          <p className="text-sm text-slate">Loading...</p>
        )}
        {readiness && <FeedbackDetails readiness={readiness} />}
      </main>
    </div>
  );
}

function FeedbackDetails({ readiness }: { readiness: DemoReadiness }) {
  // Groups still short of full credit, the ones worth the most first
  const skillGaps = readiness.skills.groups
    .filter((group) => group.out_of - group.points >= 0.01)
    .sort((a, b) => b.out_of - b.points - (a.out_of - a.points));
  const coursesLeft = readiness.courses.list.filter((course) => !course.taken);
  const { certificates } = readiness;
  const bonusLeft = certificates.max_bonus - certificates.bonus;
  const certificatesLeft = certificates.options.filter(
    (name) => !certificates.counted.includes(name),
  );

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-ink">
            How to improve your score
          </h1>
          <p className="mt-1 text-sm text-slate">
            Your readiness score is{" "}
            <span className="font-medium text-ink">
              {Math.round(readiness.overall_readiness_score)}
            </span>{" "}
            out of 100. Here&apos;s what to complete next.
          </p>
        </div>
        <Link
          to="/profileSetup"
          className="rounded-md bg-blue px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue/90"
        >
          Update skills &amp; courses
        </Link>
      </header>

      <div className="mt-8 flex flex-col gap-6">
        {readiness.next_steps.length > 0 && (
          <Card title="Start here">
            <ol className="flex flex-col gap-3">
              {readiness.next_steps.map((step, index) => (
                <li key={step.name} className="flex items-center gap-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue/15 text-sm font-semibold text-blue">
                    {index + 1}
                  </span>
                  <span className="flex-1 text-sm text-ink">
                    {step.kind === "course" ? "Take " : "Improve "}
                    {step.name}
                  </span>
                  <PointsTag>{points(step.points_available)}</PointsTag>
                </li>
              ))}
            </ol>
          </Card>
        )}

        <Card title="Skills to build">
          {skillGaps.length === 0 ? (
            <Empty>Every skill group is at Project ready. Nice work!</Empty>
          ) : (
            <ul className="flex flex-col divide-y divide-line">
              {skillGaps.map((group) => (
                <SkillFeedback key={group.key} group={group} />
              ))}
            </ul>
          )}
        </Card>

        <Card title="Courses to complete">
          {coursesLeft.length === 0 ? (
            <Empty>You&apos;ve taken every course on the list.</Empty>
          ) : (
            <ul className="flex flex-col gap-3">
              {coursesLeft.map((course) => (
                <li key={course.code} className="flex items-center gap-4">
                  <span className="flex-1 text-sm text-ink">
                    <span className="font-medium">{course.code}</span>{" "}
                    <span className="text-slate">{course.name}</span>
                  </span>
                  <PointsTag>{points(course.points)}</PointsTag>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Certificates (bonus)">
          {bonusLeft <= 0 ? (
            <Empty>You&apos;ve earned the full certificate bonus.</Empty>
          ) : (
            <>
              <p className="text-sm text-slate">
                Each certificate below adds 5 points, up to {bonusLeft} more.
              </p>
              <ul className="mt-4 flex flex-col gap-3">
                {certificatesLeft.map((name) => (
                  <li key={name} className="flex items-center gap-4">
                    <span className="flex-1 text-sm text-ink">{name}</span>
                    <PointsTag>+5 pts</PointsTag>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      </div>
    </>
  );
}

// One skill group: where the student is, what to do next, and free
// resources while they're still learning
function SkillFeedback({ group }: { group: SkillGroupResult }) {
  const tools = group.options.map((option) => option.label).join(", ");
  const left = group.out_of - group.points;

  let advice: string;
  if (!group.best_tool) {
    advice = `You haven't added a skill here yet. Start with one of: ${tools}.`;
  } else if (group.level === "Learning") {
    advice = `You're learning ${group.best_tool}. Keep practicing until you can use it on your own.`;
  } else {
    advice = `You're practicing ${group.best_tool}. Build a project with it to reach Project ready.`;
  }

  const resources =
    !group.best_tool || group.level === "Learning"
      ? (RESOURCES[group.key] ?? [])
      : [];

  return (
    <li className="py-4 first:pt-0 last:pb-0">
      <div className="flex items-center gap-4">
        <h3 className="flex-1 text-sm font-medium text-ink">
          {group.name}
          <span className="ml-2 text-xs font-normal text-slate">
            {group.level ?? "Not started"}
          </span>
        </h3>
        <PointsTag>up to {points(left)}</PointsTag>
      </div>
      <p className="mt-1 text-sm text-slate">{advice}</p>
      {resources.length > 0 && (
        <p className="mt-2 text-sm text-slate">
          Free resources:{" "}
          {resources.map((resource, index) => (
            <span key={resource.url}>
              {index > 0 && ", "}
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue underline-offset-2 hover:underline"
              >
                {resource.name}
              </a>
            </span>
          ))}
        </p>
      )}
    </li>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-line bg-surface p-8">
      <h2 className="mb-5 text-lg font-semibold text-ink">{title}</h2>
      {children}
    </section>
  );
}

function PointsTag({ children }: { children: ReactNode }) {
  return (
    <span className="shrink-0 rounded-full bg-pink/10 px-3 py-1 text-xs font-medium text-pink">
      {children}
    </span>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-slate">{children}</p>;
}
