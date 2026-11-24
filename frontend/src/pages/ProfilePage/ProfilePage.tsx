import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { ApiError, apiGet } from "../../lib/api/api";
import profileIcon from "../../assets/profile-icon.png";
import educationIcon from "../../assets/education.png";
import bookIcon from "../../assets/book.png";
import locationIcon from "../../assets/location.png";

type StudentProfile = {
  first_name: string;
  last_name: string;
  student_id: string;
  uni: string;
  major: string;
  location: string | null;
  readiness_score: number | null; // always null until the backend computes it
  graduated: boolean;
  updated_at: string; // ISO timestamp
};

// GET /api/benchmark/demo/me/ - the demo readiness score (GP-82): skills
// out of 50 + courses out of 50 + certificate bonus. Computed on request,
// never stored on the profile.
type SkillGroupResult = {
  key: string;
  name: string;
  points: number;
  out_of: number;
  best_tool: string | null; // label of the tool that earned the points
  level: string | null; // Learning / Practicing / Project ready
};
type DemoReadiness = {
  overall_readiness_score: number;
  skills: { points: number; out_of: number; groups: SkillGroupResult[] };
  courses: {
    points: number;
    out_of: number;
    list: { code: string; name: string; taken: boolean }[];
  };
  certificates: { bonus: number; max_bonus: number; counted: string[] };
  benchmark: { location: string; postings_used: number };
};

// Score bands for the readiness label - placeholder thresholds, adjust as needed
function readinessLabel(score: number): string {
  if (score >= 85) return "Career ready";
  if (score >= 60) return "Building momentum";
  if (score >= 30) return "Getting started";
  return "Just beginning";
}

function formatDateTime(iso: string | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const day = date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const time = date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${day} at ${time}`;
}

function capitalize(name: string): string {
  return name
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function ProfilePage2() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<DemoReadiness | null>(null);
  const [readinessError, setReadinessError] = useState<string | null>(null);

  useEffect(() => {
    // A missing profile or login is handled by the profile request below
    apiGet<DemoReadiness>("/api/benchmark/demo/me/")
      .then(setReadiness)
      .catch(() => setReadinessError("Could not load your readiness score."));
    apiGet<StudentProfile>("/api/auth/profile/")
      .then(setProfile)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          navigate("/profileSetup", { replace: true }); // no profile yet
        } else if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { replace: true }); // not logged in / token expired
        } else {
          setError(
            err instanceof Error ? err.message : "Could not load profile.",
          );
        }
      });
  }, [navigate]);

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto max-w-6xl px-8 pt-2 pb-12">
        {error && <p className="text-sm text-pink">{error}</p>}

        {!profile && !error && <p className="text-sm text-slate">Loading...</p>}

        {profile && (
          <Dashboard
            profile={profile}
            readiness={readiness}
            readinessError={readinessError}
          />
        )}
      </main>
    </div>
  );
}

function Dashboard({
  profile,
  readiness,
  readinessError,
}: {
  profile: StudentProfile;
  readiness: DemoReadiness | null;
  readinessError: string | null;
}) {
  const firstName = capitalize(profile.first_name);
  const fullName = `${firstName} ${capitalize(profile.last_name)}`;
  const lastUpdated = formatDateTime(profile.updated_at);

  return (
    <>
      {/* Header */}
      <header className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-ink">
            Welcome back, {firstName}
          </h1>
          <p className="mt-1 text-sm text-slate">
            {lastUpdated
              ? `Profile last updated ${lastUpdated}`
              : "Profile last updated —"}
          </p>
        </div>

        <div className="mr-8 flex items-center gap-3">
          <div className="mx-1 h-10 w-px bg-line" />
          <div className="flex items-center gap-3">
            <Avatar size="sm" />
            <div className="leading-tight">
              <p className="text-sm font-medium text-ink">{fullName}</p>
              <p className="text-xs text-slate">Student</p>
            </div>
          </div>
        </div>
      </header>

      {/* Top row */}
      <section className="mt-8 grid gap-6 lg:grid-cols-3">
        {/* Student profile */}
        <Card>
          <CardTitle>Student profile</CardTitle>
          <div className="mt-5 flex items-center gap-4">
            <Avatar size="lg" />
            <div>
              <h2 className="text-2xl font-medium text-ink">{fullName}</h2>
              <p className="text-sm text-slate">ID {profile.student_id}</p>
            </div>
          </div>

          <ul className="mt-6 flex flex-col gap-3 text-sm text-ink">
            <IconRow icon={educationIcon}>{profile.uni}</IconRow>
            <IconRow icon={bookIcon}>{profile.major}</IconRow>
            <IconRow icon={locationIcon}>{profile.location || "—"}</IconRow>
          </ul>
        </Card>

        {/* Career readiness - the demo score and what makes it up */}
        <Card className="lg:col-span-2">
          <ReadinessDetails readiness={readiness} error={readinessError} />
        </Card>
      </section>

      {/* Bottom row */}
      <section className="mt-6">
        {/* Readiness over time */}
        <Card>
          <div className="flex items-center justify-between">
            <CardTitle>Readiness over time</CardTitle>
            <span className="text-xs text-slate">Last 6 months</span>
          </div>
          <div className="mt-5 flex h-64 items-center justify-center rounded-xl border border-dashed border-line px-6 text-center text-sm text-slate">
            Score history isn&apos;t tracked yet. Your readiness trend will
            appear here once scores are recorded.
          </div>
        </Card>
      </section>
    </>
  );
}

/* Building blocks */

function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-line bg-surface p-6 ${className}`}
    >
      {children}
    </div>
  );
}

function CardTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-base font-semibold text-ink">{children}</h3>;
}

function Pill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-block rounded-full bg-line px-3 py-1 text-xs font-medium text-ink">
      {children}
    </span>
  );
}

function Avatar({ size }: { size: "sm" | "lg" }) {
  const sizing = size === "lg" ? "h-16 w-16 p-3" : "h-10 w-10 p-2";
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full bg-line ${sizing}`}
    >
      <img src={profileIcon} alt="" className="h-full w-full object-contain" />
    </div>
  );
}

function IconRow({ icon, children }: { icon: string; children: ReactNode }) {
  return (
    <li className="flex items-center gap-3">
      <img src={icon} alt="" className="h-[18px] w-[18px] invert opacity-70" />
      <span>{children}</span>
    </li>
  );
}

function ReadinessGauge({ score }: { score: number | null }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const clamped = score == null ? 0 : Math.min(Math.max(score, 0), 100);
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="relative h-40 w-40">
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          strokeWidth="10"
          className="stroke-line"
        />
        {score != null && (
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="stroke-blue"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-semibold text-ink">
          {score != null ? Math.round(score) : "—"}
        </span>
        <span className="text-xs text-slate">
          {score != null ? "out of 100" : "not yet scored"}
        </span>
      </div>
    </div>
  );
}

function ReadinessDetails({
  readiness,
  error,
}: {
  readiness: DemoReadiness | null;
  error: string | null;
}) {
  const score = readiness?.overall_readiness_score ?? null;
  const [showBreakdown, setShowBreakdown] = useState(false);

  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <CardTitle>Career readiness</CardTitle>
        <Pill>{score != null ? readinessLabel(score) : "Not calculated"}</Pill>
      </div>

      {error && <p className="mt-4 text-sm text-pink">{error}</p>}
      {!readiness && !error && (
        <p className="mt-4 text-sm text-slate">Calculating...</p>
      )}

      <div className="mt-6 flex flex-col items-center gap-8 sm:flex-row">
        <ReadinessGauge score={score} />

        {readiness && (
          <div className="flex w-full flex-1 flex-col gap-4">
            <ScoreBar
              label="Skills"
              points={readiness.skills.points}
              outOf={readiness.skills.out_of}
            />
            <ScoreBar
              label="Courses"
              points={readiness.courses.points}
              outOf={readiness.courses.out_of}
              note={`${readiness.courses.list.filter((c) => c.taken).length} of ${readiness.courses.list.length} taken`}
            />
            <ScoreBar
              label="Certificates"
              points={readiness.certificates.bonus}
              outOf={readiness.certificates.max_bonus}
              note={readiness.certificates.counted.join(", ") || "None yet"}
            />
            <p className="text-xs text-slate">
              Based on {readiness.benchmark.postings_used} Software Developer
              job postings in {readiness.benchmark.location}.
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setShowBreakdown(true)}
                className="rounded-full border border-blue px-4 py-2 text-sm font-medium text-blue transition-colors hover:bg-blue hover:text-white"
              >
                View skill breakdown
              </button>
              {/* The setup page edits an existing profile; the score is
                  recalculated from the saved records on the way back */}
              <Link
                to="/profileSetup"
                className="rounded-full bg-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue/90"
              >
                Update skills & courses
              </Link>
            </div>
          </div>
        )}
      </div>

      {readiness && showBreakdown && (
        <Modal title="Skill breakdown" onClose={() => setShowBreakdown(false)}>
          <p className="text-sm text-slate">
            {readiness.skills.points.toFixed(1)} of {readiness.skills.out_of}{" "}
            skill points. Your best tool in each area counts.
          </p>
          <ul className="mt-5 flex flex-col gap-4">
            {readiness.skills.groups.map((group) => (
              <li key={group.key}>
                <ScoreBar
                  label={group.name}
                  points={group.points}
                  outOf={group.out_of}
                  note={
                    group.best_tool
                      ? `${group.best_tool} - ${group.level}`
                      : "Not started"
                  }
                  small
                />
              </li>
            ))}
          </ul>
        </Modal>
      )}
    </>
  );
}

function ScoreBar({
  label,
  points,
  outOf,
  note,
  small = false,
}: {
  label: string;
  points: number;
  outOf: number;
  note?: string;
  small?: boolean;
}) {
  const percent = outOf > 0 ? Math.min(100, (points / outOf) * 100) : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className={small ? "text-ink" : "font-medium text-ink"}>
          {label}
        </span>
        <span className="shrink-0 text-slate">
          {points.toFixed(1)} / {outOf.toFixed(outOf % 1 ? 1 : 0)}
        </span>
      </div>
      <div
        className={`mt-1 w-full overflow-hidden rounded-full bg-line ${small ? "h-1.5" : "h-2"}`}
        role="progressbar"
        aria-label={label}
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-blue"
          style={{ width: `${percent}%` }}
        />
      </div>
      {note && <p className="mt-1 text-xs text-slate">{note}</p>}
    </div>
  );
}

// A pop-up over the page. Closes on ×, Escape, or a click on the backdrop.
function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-line bg-surface p-6"
      >
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold text-ink">{title}</h3>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="px-2 text-2xl leading-none text-slate hover:text-pink"
          >
            ×
          </button>
        </div>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}
