import Navbar from "../../components/Navbar/Navbar";
import { Link, useNavigate } from "react-router-dom";
import { logout } from "../../lib/api/auth";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  ApiError,
  apiDelete,
  apiFetch,
  apiGet,
  apiPatch,
} from "../../lib/api/api";

// The demo is scoped to one school, major, location and role (GP-82), so
// these are picked from a set instead of typed. Values must match the
// backend's demo scope (benchmarks/job_benchmark_demo.py).
const UNIVERSITIES = ["Old Dominion University"];
const MAJORS = ["Computer Science"];
const LOCATIONS = ["Norfolk, VA"];
// value = SOC code saved as target_job
const TARGET_ROLES = [{ value: "15-1252", label: "Software Developer" }];

// TakenClass.semester choices on the backend
const SEMESTERS = [
  { value: "fall", label: "Fall" },
  { value: "spring", label: "Spring" },
  { value: "summer", label: "Summer" },
  { value: "winter", label: "Winter" },
];

// The courses and skills that count toward readiness come from the backend
// (GET /api/benchmark/demo/options/), so the lists match its scoring.
type Course = { code: string; name: string };
// name = exact O*NET name saved on the Skill row; label = what's shown
type Tool = { name: string; label: string };
type SkillGroup = { key: string; name: string; points: number; tools: Tool[] };
// value = saved as proficiency_level; label = Learning / Practicing / Project ready
type Level = { value: string; label: string; credit: number };
type DemoOptions = {
  courses: Course[];
  skill_groups: SkillGroup[];
  levels: Level[];
  certificates: string[]; // names that earn the readiness bonus
};

// Certificate.issuing_organization is required on the backend; the demo's
// certificates all start with their issuer ('AWS Certified ...',
// 'CompTIA Security+', 'Microsoft Certified: ...').
function issuerOf(certificate: string): string {
  return certificate.split(/[\s:]/)[0];
}

// What the student picked for one course
type CourseTerm = { semester: string; year: string };

const FIELD_CLASS =
  "rounded-md border border-line bg-transparent px-4 py-3 text-base text-ink outline-none focus:border-blue";
const SMALL_FIELD_CLASS =
  "rounded-md border border-line bg-transparent px-3 py-2 text-sm text-ink outline-none focus:border-blue";

// Defaults a newly picked course to the current term
function currentTerm(): CourseTerm {
  const now = new Date();
  const month = now.getMonth(); // 0 = January
  const semester = month < 5 ? "spring" : month < 8 ? "summer" : "fall";
  return { semester, year: String(now.getFullYear()) };
}

function SelectField({
  label,
  name,
  options,
  defaultValue = "",
}: {
  label: string;
  name: string;
  options: { value: string; label: string }[];
  defaultValue?: string;
}) {
  return (
    <label className="flex flex-col gap-2 text-sm font-medium text-ink">
      {label}
      <select
        name={name}
        required
        defaultValue={defaultValue}
        className={FIELD_CLASS}
      >
        <option value="" disabled />
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

const asOptions = (values: string[]) =>
  values.map((value) => ({ value, label: value }));

function SectionHeading({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="border-b border-line pb-2">
      <h3 className="text-lg font-semibold text-ink">{title}</h3>
      {hint && <p className="mt-1 text-sm text-slate">{hint}</p>}
    </div>
  );
}

// One choice in a MultiSelectDropdown: `label` is shown in the closed box
// once picked, `detail` only in the open list.
type Choice = { value: string; label: string; detail?: string };

// A dropdown that stays open while several choices are ticked, and closes
// on a click outside it.
function MultiSelectDropdown({
  id,
  label,
  choices,
  selected,
  onToggle,
  placeholder = "",
}: {
  id: string;
  label: string;
  choices: Choice[];
  selected: (value: string) => boolean;
  onToggle: (value: string) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const dropdown = useRef<HTMLDivElement>(null);
  const picked = choices.filter((choice) => selected(choice.value));

  useEffect(() => {
    if (!open) return;
    function closeOnOutsideClick(event: MouseEvent) {
      if (!dropdown.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, [open]);

  return (
    <div ref={dropdown} className="relative flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </label>
      <button
        id={id}
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((isOpen) => !isOpen)}
        className={`${FIELD_CLASS} flex items-center justify-between gap-3 text-left`}
      >
        <span className={`truncate ${picked.length ? "" : "text-slate"}`}>
          {picked.length
            ? picked.map((choice) => choice.label).join(", ")
            : placeholder}
        </span>
        <span aria-hidden="true">▾</span>
      </button>

      {open && (
        <ul className="absolute top-full z-10 mt-1 max-h-72 w-full overflow-auto rounded-md border border-line bg-surface py-1 shadow-lg">
          {choices.map((choice) => {
            const choiceId = `${id}-${choice.value.replace(/\W+/g, "")}`;
            return (
              <li key={choice.value}>
                <label
                  htmlFor={choiceId}
                  className="flex cursor-pointer items-center gap-3 px-4 py-2 text-sm hover:bg-canvas"
                >
                  <input
                    id={choiceId}
                    type="checkbox"
                    checked={selected(choice.value)}
                    onChange={() => onToggle(choice.value)}
                    className="h-4 w-4 accent-blue"
                  />
                  <span className="font-semibold text-ink">{choice.label}</span>
                  {choice.detail && (
                    <span className="text-slate">{choice.detail}</span>
                  )}
                </label>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// A picked item under a dropdown: its name, its controls, and ✕ to remove it.
function PickedRow({
  title,
  detail,
  onRemove,
  children,
}: {
  title: string;
  detail?: string;
  onRemove: () => void;
  children: ReactNode;
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3">
      <p className="text-sm">
        <span className="font-semibold text-ink">{title}</span>{" "}
        {detail && <span className="text-slate">{detail}</span>}
      </p>
      <div className="flex items-center gap-2">
        {children}
        <button
          type="button"
          aria-label={`Remove ${title}`}
          onClick={onRemove}
          className="px-2 text-lg text-slate hover:text-pink"
        >
          ×
        </button>
      </div>
    </li>
  );
}

const PICKED_LIST_CLASS = "divide-y divide-line rounded-md border border-line px-4";

function CoursesSection({
  courses,
  picked,
  onToggle,
  onChange,
}: {
  courses: Course[];
  picked: Record<string, CourseTerm>;
  onToggle: (code: string) => void;
  onChange: (code: string, term: CourseTerm) => void;
}) {
  const pickedList = courses.filter((course) => picked[course.code]);

  return (
    <div className="grid gap-3">
      <MultiSelectDropdown
        id="courses-dropdown"
        label="Courses"
        choices={courses.map((course) => ({
          value: course.code,
          label: course.code,
          detail: course.name,
        }))}
        selected={(code) => Boolean(picked[code])}
        onToggle={onToggle}
        placeholder="Select courses…"
      />

      {pickedList.length > 0 && (
        <ul className={PICKED_LIST_CLASS}>
          {pickedList.map((course) => {
            const term = picked[course.code];
            return (
              <PickedRow
                key={course.code}
                title={course.code}
                detail={course.name}
                onRemove={() => onToggle(course.code)}
              >
                <select
                  aria-label={`${course.code} semester`}
                  value={term.semester}
                  onChange={(e) =>
                    onChange(course.code, { ...term, semester: e.target.value })
                  }
                  className={SMALL_FIELD_CLASS}
                >
                  {SEMESTERS.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
                <input
                  aria-label={`${course.code} year`}
                  type="number"
                  required
                  min={1900}
                  max={new Date().getFullYear() + 1}
                  value={term.year}
                  onChange={(e) =>
                    onChange(course.code, { ...term, year: e.target.value })
                  }
                  className={`${SMALL_FIELD_CLASS} w-24`}
                />
              </PickedRow>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// Learning / Practicing / Project ready as a row of toggle buttons
function LevelPicker({
  tool,
  levels,
  value,
  onChange,
}: {
  tool: Tool;
  levels: Level[];
  value: string;
  onChange: (level: string) => void;
}) {
  return (
    <div
      role="group"
      aria-label={`${tool.label} level`}
      className="flex overflow-hidden rounded-md border border-line text-xs"
    >
      {levels.map((level) => (
        <button
          key={level.value}
          type="button"
          aria-pressed={value === level.value}
          onClick={() => onChange(level.value)}
          className={`px-3 py-2 transition-colors ${
            value === level.value
              ? "bg-blue text-white"
              : "text-slate hover:bg-canvas"
          }`}
        >
          {level.label}
        </button>
      ))}
    </div>
  );
}

// One multi-select per skill group; each picked tool gets a level. Only
// the best tool in a group counts toward readiness, so one is enough.
function SkillsSection({
  groups,
  levels,
  picked,
  onToggle,
  onChange,
}: {
  groups: SkillGroup[];
  levels: Level[];
  picked: Record<string, string>;
  onToggle: (name: string) => void;
  onChange: (name: string, level: string) => void;
}) {
  return (
    <div className="grid gap-6">
      {groups.map((group) => {
        const pickedTools = group.tools.filter((tool) => picked[tool.name]);
        return (
          <div key={group.key} className="grid gap-3">
            <MultiSelectDropdown
              id={`skills-${group.key}`}
              label={group.name}
              choices={group.tools.map((tool) => ({
                value: tool.name,
                label: tool.label,
              }))}
              selected={(name) => Boolean(picked[name])}
              onToggle={onToggle}
            />

            {pickedTools.length > 0 && (
              <ul className={PICKED_LIST_CLASS}>
                {pickedTools.map((tool) => (
                  <PickedRow
                    key={tool.name}
                    title={tool.label}
                    onRemove={() => onToggle(tool.name)}
                  >
                    <LevelPicker
                      tool={tool}
                      levels={levels}
                      value={picked[tool.name]}
                      onChange={(level) => onChange(tool.name, level)}
                    />
                  </PickedRow>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

// The caller's saved records, as the list endpoints return them (paginated)
type Page<T> = { results: T[] };
type StudentProfile = {
  student_id: string;
  uni: string;
  major: string;
  location: string;
  target_job: string | null;
};
type SavedClass = { id: string; course_code: string; semester: string; year: number };
type SavedSkill = { id: string; name: string; proficiency_level: string };
type SavedCertificate = { id: string; name: string };

// What's on the backend right now, keyed like the picked state, with each
// record's id so it can be updated or deleted. Kept current after every
// request, so a retry after a partial failure only sends what's left.
type Saved = {
  profile: boolean;
  courses: Record<string, CourseTerm & { id: string }>;
  skills: Record<string, { id: string; level: string }>;
  certificates: Record<string, string>; // name -> id
};

// Older rows may say 'advanced' or be unrated - show them as the demo's
// Practicing / Learning (same mapping as the backend's scoring_demo.py).
function demoLevel(level: string): string {
  if (level === "advanced") return "intermediate";
  return level || "beginner";
}

// Without a profile this page creates one; with one it edits it, loading
// the student's saved courses, skills and certificates into the pickers.
export default function ProfileSetupPage() {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [options, setOptions] = useState<DemoOptions | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  // null while checking whether a profile exists
  const [mode, setMode] = useState<"create" | "edit" | null>(null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [pickedCourses, setPickedCourses] = useState<Record<string, CourseTerm>>({});
  // O*NET tool name -> proficiency_level
  const [pickedSkills, setPickedSkills] = useState<Record<string, string>>({});
  const [pickedCertificates, setPickedCertificates] = useState<string[]>([]);
  const saved = useRef<Saved>({
    profile: false,
    courses: {},
    skills: {},
    certificates: {},
  });

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  function toggleCourse(code: string) {
    setPickedCourses((picked) => {
      const next = { ...picked };
      if (next[code]) delete next[code];
      else next[code] = currentTerm();
      return next;
    });
  }

  function changeCourseTerm(code: string, term: CourseTerm) {
    setPickedCourses((picked) => ({ ...picked, [code]: term }));
  }

  function toggleSkill(name: string) {
    setPickedSkills((picked) => {
      const next = { ...picked };
      if (next[name]) delete next[name];
      else next[name] = options?.levels[0]?.value ?? "beginner"; // start at Learning
      return next;
    });
  }

  function toggleCertificate(name: string) {
    setPickedCertificates((picked) =>
      picked.includes(name)
        ? picked.filter((certificate) => certificate !== name)
        : [...picked, name],
    );
  }

  function changeSkillLevel(name: string, level: string) {
    setPickedSkills((picked) => ({ ...picked, [name]: level }));
  }

  // Add what's newly picked, update what changed, delete what was removed.
  // Only items on the demo's lists are touched.
  async function syncCourses(courses: Course[]) {
    const have = saved.current.courses;
    for (const course of courses) {
      const want = pickedCourses[course.code];
      const current = have[course.code];
      if (want && !current) {
        const created = await apiFetch<{ id: string }>(
          "/api/auth/profile/classes/",
          {
            course_code: course.code,
            course_name: course.name,
            semester: want.semester,
            year: Number(want.year),
          },
          true,
        );
        have[course.code] = { ...want, id: created.id };
      } else if (!want && current) {
        await apiDelete(`/api/auth/profile/classes/${current.id}/`);
        delete have[course.code];
      } else if (
        want &&
        current &&
        (want.semester !== current.semester || want.year !== current.year)
      ) {
        await apiPatch(`/api/auth/profile/classes/${current.id}/`, {
          semester: want.semester,
          year: Number(want.year),
        });
        have[course.code] = { ...want, id: current.id };
      }
    }
  }

  async function syncSkills(groups: SkillGroup[]) {
    const have = saved.current.skills;
    for (const tool of groups.flatMap((group) => group.tools)) {
      const want = pickedSkills[tool.name];
      const current = have[tool.name];
      if (want && !current) {
        const created = await apiFetch<{ id: string }>(
          "/api/auth/profile/skills/",
          { name: tool.name, proficiency_level: want },
          true,
        );
        have[tool.name] = { id: created.id, level: want };
      } else if (!want && current) {
        await apiDelete(`/api/auth/profile/skills/${current.id}/`);
        delete have[tool.name];
      } else if (want && current && want !== current.level) {
        await apiPatch(`/api/auth/profile/skills/${current.id}/`, {
          proficiency_level: want,
        });
        have[tool.name] = { id: current.id, level: want };
      }
    }
  }

  async function syncCertificates(certificates: string[]) {
    const have = saved.current.certificates;
    for (const name of certificates) {
      const want = pickedCertificates.includes(name);
      if (want && !have[name]) {
        const created = await apiFetch<{ id: string }>(
          "/api/auth/profile/certificates/",
          { name, issuing_organization: issuerOf(name) },
          true,
        );
        have[name] = created.id;
      } else if (!want && have[name]) {
        await apiDelete(`/api/auth/profile/certificates/${have[name]}/`);
        delete have[name];
      }
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);

    const form = new FormData(event.currentTarget);
    const about = {
      major: form.get("major"),
      uni: form.get("uni"),
      location: form.get("location") ?? "",
      target_job: form.get("target_job"),
    };
    try {
      // The profile has to exist before courses and skills can be attached.
      if (!saved.current.profile) {
        await apiFetch(
          "/api/auth/profile/",
          {
            ...about,
            student_id: form.get("student_id"),
            graduated: form.get("graduated") === "on", // unchecked box isn't in FormData
          },
          true, // send the access token
        );
        saved.current.profile = true;
      } else {
        // student_id can't be changed after the profile is created
        await apiPatch("/api/auth/profile/", about);
      }

      if (options) {
        await syncCourses(options.courses);
        await syncSkills(options.skill_groups);
        await syncCertificates(options.certificates);
      }

      navigate("/profile", { replace: true });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save your profile.",
      );
      setSubmitting(false);
    }
  }

  useEffect(() => {
    apiGet<{ first_name: string }>("/api/auth/me")
      .then((user) => setFirstName(user.first_name))
      .catch(() => setFirstName(null));
    apiGet<DemoOptions>("/api/benchmark/demo/options/")
      .then(setOptions)
      .catch(() => setOptionsError("Could not load the course and skill lists."));

    async function loadSaved() {
      const existing = await apiGet<StudentProfile>("/api/auth/profile/");
      const [classes, skills, certificates] = await Promise.all([
        apiGet<Page<SavedClass>>("/api/auth/profile/classes/"),
        apiGet<Page<SavedSkill>>("/api/auth/profile/skills/"),
        apiGet<Page<SavedCertificate>>("/api/auth/profile/certificates/"),
      ]);

      const courses: Saved["courses"] = {};
      for (const c of classes.results) {
        // A retaken course has two rows - the first one is edited
        courses[c.course_code] ??= {
          id: c.id,
          semester: c.semester,
          year: String(c.year),
        };
      }
      const savedSkills: Saved["skills"] = {};
      for (const s of skills.results) {
        savedSkills[s.name] = { id: s.id, level: demoLevel(s.proficiency_level) };
      }
      const savedCertificates: Saved["certificates"] = {};
      for (const c of certificates.results) savedCertificates[c.name] = c.id;

      saved.current = {
        profile: true,
        courses,
        skills: savedSkills,
        certificates: savedCertificates,
      };
      setPickedCourses(
        Object.fromEntries(
          Object.entries(courses).map(([code, { semester, year }]) => [
            code,
            { semester, year },
          ]),
        ),
      );
      setPickedSkills(
        Object.fromEntries(
          Object.entries(savedSkills).map(([name, { level }]) => [name, level]),
        ),
      );
      setPickedCertificates(Object.keys(savedCertificates));
      setProfile(existing);
      setMode("edit");
    }

    loadSaved().catch((err) => {
      if (err instanceof ApiError && err.status === 404) {
        setMode("create"); // no profile yet
      } else if (err instanceof ApiError && err.status === 401) {
        navigate("/login", { replace: true }); // not logged in / token expired
      } else {
        setError(
          err instanceof Error ? err.message : "Could not load your profile.",
        );
        setMode("create");
      }
    });
  }, [navigate]);

  const editing = mode === "edit";
  const pickedCourseCount = Object.keys(pickedCourses).length;
  const loading = !options && !optionsError;
  const name = firstName
    ? ` ${firstName.charAt(0).toUpperCase()}${firstName.slice(1)}`
    : "";

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto flex max-w-6xl justify-center px-8 py-12">
        {/* Page-like card: letter-paper width, grows down as sections are added */}
        <div className="w-full max-w-4xl rounded-2xl border border-line bg-surface p-12">
          <h1 className="text-4xl font-medium text-ink">
            {editing ? `Update your profile${name && `,${name}`}` : `Hi${name}, welcome to GradPace`}
          </h1>
          <h2 className="mt-2 text-xl font-medium text-slate">
            {editing
              ? "Keep your courses, skills and certificates up to date."
              : "Tell us a little more about you."}
          </h2>
          <p className="mt-3 text-sm text-slate">
            {editing ? (
              <Link to="/profile" className="text-ink hover:text-pink">
                Back to your profile
              </Link>
            ) : (
              <>
                Want to finish setting up later?{" "}
                <button
                  type="button"
                  onClick={handleLogout}
                  className="text-ink hover:text-pink"
                >
                  Log out
                </button>
              </>
            )}
          </p>

          {error && <p className="mt-6 text-sm text-pink">{error}</p>}
          {mode === null && !error && (
            <p className="mt-8 text-sm text-slate">Loading...</p>
          )}

          {mode !== null && (
            <form className="mt-8 flex flex-col gap-10" onSubmit={handleSubmit}>
              <section className="grid gap-4">
                <SectionHeading title="About you" />
                <label className="flex flex-col gap-2 text-sm font-medium text-ink">
                  Student ID
                  <input
                    type="text"
                    name="student_id"
                    required
                    disabled={editing}
                    defaultValue={profile?.student_id ?? ""}
                    title={editing ? "Your student ID can't be changed" : undefined}
                    className={`${FIELD_CLASS} disabled:opacity-60`}
                  />
                </label>

                <SelectField
                  label="University"
                  name="uni"
                  options={asOptions(UNIVERSITIES)}
                  defaultValue={profile?.uni}
                />
                <SelectField
                  label="Major"
                  name="major"
                  options={asOptions(MAJORS)}
                  defaultValue={profile?.major}
                />
                <SelectField
                  label="Location"
                  name="location"
                  options={asOptions(LOCATIONS)}
                  defaultValue={profile?.location}
                />
                <SelectField
                  label="Target role"
                  name="target_job"
                  options={TARGET_ROLES}
                  defaultValue={profile?.target_job ?? undefined}
                />
              </section>

              {optionsError && <p className="text-sm text-pink">{optionsError}</p>}

              <section className="grid gap-2">
                <SectionHeading
                  title="Courses taken"
                  hint="Select every course you've completed or are taking now, then set when you took it."
                />
                {loading && <p className="text-sm text-slate">Loading courses...</p>}
                {options && (
                  <>
                    <CoursesSection
                      courses={options.courses}
                      picked={pickedCourses}
                      onToggle={toggleCourse}
                      onChange={changeCourseTerm}
                    />
                    <p className="text-sm text-slate">
                      {pickedCourseCount} of {options.courses.length} selected
                    </p>
                  </>
                )}
              </section>

              <section className="grid gap-4">
                <SectionHeading
                  title="Skills"
                  hint="For each area, select the tools you've used and how far along you are: Learning (taking a course or tutorial), Practicing (used it in assignments), or Project ready (built a working project with it). Your best tool in each area counts."
                />
                {loading && <p className="text-sm text-slate">Loading skills...</p>}
                {options && (
                  <SkillsSection
                    groups={options.skill_groups}
                    levels={options.levels}
                    picked={pickedSkills}
                    onToggle={toggleSkill}
                    onChange={changeSkillLevel}
                  />
                )}
              </section>

              <section className="grid gap-4">
                <SectionHeading
                  title="Certificates"
                  hint="Optional - select any certifications you've earned. Each one adds a bonus to your readiness."
                />
                {loading && (
                  <p className="text-sm text-slate">Loading certificates...</p>
                )}
                {options && (
                  <div className="grid gap-3">
                    <MultiSelectDropdown
                      id="certificates-dropdown"
                      label="Certificates"
                      choices={options.certificates.map((certificate) => ({
                        value: certificate,
                        label: certificate,
                      }))}
                      selected={(certificate) =>
                        pickedCertificates.includes(certificate)
                      }
                      onToggle={toggleCertificate}
                    />
                    {pickedCertificates.length > 0 && (
                      <ul className={PICKED_LIST_CLASS}>
                        {pickedCertificates.map((certificate) => (
                          <PickedRow
                            key={certificate}
                            title={certificate}
                            onRemove={() => toggleCertificate(certificate)}
                          >
                            <span className="text-sm text-slate">
                              {issuerOf(certificate)}
                            </span>
                          </PickedRow>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </section>

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-full bg-blue py-3 text-sm font-semibold text-white transition-colors hover:bg-blue/90 disabled:opacity-60"
              >
                {editing
                  ? submitting
                    ? "Saving..."
                    : "Save changes"
                  : submitting
                    ? "Creating..."
                    : "Create Profile"}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
