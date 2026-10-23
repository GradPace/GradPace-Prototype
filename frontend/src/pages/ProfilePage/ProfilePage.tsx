import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
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

// Fields counted toward "Profile completeness"
const COMPLETENESS_FIELDS = [
  "first_name",
  "last_name",
  "student_id",
  "uni",
  "major",
  "location",
] as const;

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

function formatDate(iso: string | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
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

  useEffect(() => {
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

        {profile && <Dashboard profile={profile} />}
      </main>
    </div>
  );
}

function Dashboard({ profile }: { profile: StudentProfile }) {
  const firstName = capitalize(profile.first_name);
  const fullName = `${firstName} ${capitalize(profile.last_name)}`;
  const lastUpdated = formatDateTime(profile.updated_at);

  const filled = COMPLETENESS_FIELDS.filter((key) =>
    Boolean(profile[key]?.toString().trim()),
  ).length;
  const completeness = Math.round((filled / COMPLETENESS_FIELDS.length) * 100);

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

        {/* Career readiness */}
        <Card>
          <div className="flex items-center justify-between gap-2">
            <CardTitle>Career readiness</CardTitle>
            <Pill>
              {profile.readiness_score != null
                ? readinessLabel(profile.readiness_score)
                : "Not calculated"}
            </Pill>
          </div>

          <div className="mt-6 flex justify-center">
            <ReadinessGauge score={profile.readiness_score ?? null} />
          </div>

          <p className="mt-6 text-center">
            <button
              type="button"
              disabled
              title="Coming soon"
              className="text-sm font-medium text-blue disabled:cursor-not-allowed disabled:opacity-60"
            >
              See what moves your score
            </button>
          </p>
        </Card>

        {/* Right column: graduation + completeness */}
        <div className="flex flex-col gap-6">
          <Card>
            <p className="text-sm font-medium text-slate">Graduation status</p>
            <p className="mt-2 text-2xl font-semibold text-ink">
              {profile.graduated ? "Graduated" : "Current student"}
            </p>
            <div className="mt-3">
              <Pill>
                {profile.graduated ? "Graduated" : "Not yet graduated"}
              </Pill>
            </div>
          </Card>

          <Card>
            <p className="text-sm font-medium text-slate">
              Profile completeness
            </p>
            <p className="mt-2 text-3xl font-semibold text-ink">
              {completeness}%
            </p>
            <div
              className="mt-3 h-2 w-full overflow-hidden rounded-full bg-line"
              role="progressbar"
              aria-valuenow={completeness}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full rounded-full bg-blue"
                style={{ width: `${completeness}%` }}
              />
            </div>
            <p className="mt-3 text-xs text-slate">
              {filled} of {COMPLETENESS_FIELDS.length} fields filled
            </p>
          </Card>
        </div>
      </section>

      {/* Bottom row */}
      <section className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Readiness over time */}
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between">
            <CardTitle>Readiness over time</CardTitle>
            <span className="text-xs text-slate">Last 6 months</span>
          </div>
          <div className="mt-5 flex h-64 items-center justify-center rounded-xl border border-dashed border-line px-6 text-center text-sm text-slate">
            Score history isn&apos;t tracked yet. Your readiness trend will
            appear here once scores are recorded.
          </div>
        </Card>

        {/* Student record */}
        <Card>
          <CardTitle>Student record</CardTitle>
          <dl className="mt-4">
            <RecordRow label="Student ID" value={profile.student_id} />
            <RecordRow label="University" value={profile.uni} />
            <RecordRow label="Major" value={profile.major} />
            <RecordRow label="Location" value={profile.location} />
            <RecordRow
              label="Graduated"
              value={profile.graduated ? "Yes" : "No"}
            />
            <RecordRow
              label="Last updated"
              value={formatDate(profile.updated_at)}
              last
            />
          </dl>
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

function RecordRow({
  label,
  value,
  last = false,
}: {
  label: string;
  value: string | null;
  last?: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between gap-4 py-3 text-sm ${
        last ? "" : "border-b border-line"
      }`}
    >
      <dt className="text-slate">{label}</dt>
      <dd className="text-right font-medium text-ink">{value || "—"}</dd>
    </div>
  );
}

function ReadinessGauge({ score }: { score: number | null }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  // const clamped = score == null ? 0 : Math.min(Math.max(score, 0), 100);
  // const offset = circumference * (1 - clamped / 100);
  score = 40;

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
            // strokeDashoffset={offset}
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
