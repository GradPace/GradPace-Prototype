import { useEffect, useState } from "react";
import {
  getSurveyResults,
  type IndustryResult,
  type RatingSummary,
  type SurveyResults,
} from "../../lib/api/admin";
import { Card, Stat, Table, Td, Th } from "./ui";

type Loaded = { data: SurveyResults } | { error: string };

// The rating questions, as the survey asks them.
const RATING_LABELS = {
  preparedness_rating: "How prepared alumni felt for their first job",
  platform_helpfulness_rating: "How much GradPace helped them get there",
} as const;

function average(value: number | null): string | null {
  return value === null ? null : value.toFixed(1);
}

// Alumni Survey results (GET /api/survey/admin/results/): ratings, industries,
// skills and feedback. Aggregates only - the backend sends no identities.
export default function SurveyResultsTab() {
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let stale = false;
    getSurveyResults()
      .then((data) => !stale && setLoaded({ data }))
      .catch(
        (err) =>
          !stale &&
          setLoaded({
            error: err instanceof Error ? err.message : "Something went wrong.",
          }),
      );
    return () => {
      stale = true;
    };
  }, []);

  if (!loaded) {
    return <p className="text-sm text-slate">Loading survey results...</p>;
  }
  if ("error" in loaded) {
    return (
      <p role="alert" className="text-sm text-pink">
        {loaded.error}
      </p>
    );
  }

  const results = loaded.data;
  if (results.response_count === 0) {
    return (
      <Card>
        <h2 className="text-base font-semibold text-ink">Survey results</h2>
        <p className="mt-2 text-sm text-slate">No survey responses yet.</p>
      </Card>
    );
  }

  const { ratings } = results;
  return (
    <div className="flex flex-col gap-6">
      <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Responses" value={results.response_count} />
        <Stat
          label="Average preparedness"
          value={average(ratings.preparedness_rating.average) ?? "No data"}
        />
        <Stat
          label="Average GradPace helpfulness"
          value={
            average(ratings.platform_helpfulness_rating.average) ?? "No data"
          }
        />
        <Stat
          label="Latest response"
          value={
            <span className="text-base">
              {results.latest_submitted_at
                ? new Date(results.latest_submitted_at).toLocaleDateString()
                : "No data"}
            </span>
          }
        />
      </section>

      <Card>
        <h2 className="text-base font-semibold text-ink">Ratings</h2>
        <div className="mt-5 grid gap-8 md:grid-cols-2">
          {(Object.keys(RATING_LABELS) as (keyof typeof RATING_LABELS)[]).map(
            (field) => (
              <RatingBars
                key={field}
                field={field}
                label={RATING_LABELS[field]}
                summary={ratings[field]}
                total={results.response_count}
              />
            ),
          )}
        </div>
      </Card>

      <Industries industries={results.by_industry} />

      <section className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-base font-semibold text-ink">Top skills</h2>
          <p className="mt-1 text-xs text-slate">
            The skills alumni use most in their current role.
          </p>
          <CountTable
            heading="Skill"
            rows={results.top_skills.map((skill) => ({
              key: skill.name,
              label: skill.label,
              count: skill.count,
            }))}
          />
        </Card>
        <Card>
          <h2 className="text-base font-semibold text-ink">Suggested skills</h2>
          <p className="mt-1 text-xs text-slate">
            Newer skills alumni say students should focus on (top 20).
          </p>
          <CountTable
            heading="Skill"
            rows={results.suggested_skills.map((skill) => ({
              key: skill.skill,
              label: skill.skill,
              count: skill.count,
            }))}
          />
        </Card>
      </section>

      <Card>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-base font-semibold text-ink">Feedback</h2>
          {results.feedback.length < results.feedback_count && (
            <p className="text-xs text-slate">
              Showing {results.feedback.length} of {results.feedback_count}
            </p>
          )}
        </div>
        <ul className="mt-4 flex flex-col divide-y divide-line">
          {results.feedback.map((item, index) => (
            <li key={index} className="py-3">
              <p className="whitespace-pre-line text-sm text-ink">
                {item.text}
              </p>
              <p className="mt-1 text-xs text-slate">
                {new Date(item.submitted_at).toLocaleDateString()}
              </p>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

// One bar per rating 1-5. Widths are each value's share of all responses, so
// the two ratings' bars can be compared. The count beside it is the number.
function RatingBars({
  field,
  label,
  summary,
  total,
}: {
  field: string;
  label: string;
  summary: RatingSummary;
  total: number;
}) {
  return (
    <figure>
      <figcaption className="text-sm font-medium text-ink">{label}</figcaption>
      <ul className="mt-3 flex flex-col gap-2">
        {summary.distribution.map(({ value, count }) => (
          <li
            key={value}
            data-testid={`${field}-${value}`}
            className="flex items-center gap-3 text-sm"
          >
            <span className="w-4 text-slate">{value}</span>
            <div
              aria-hidden="true"
              className="h-2 flex-1 overflow-hidden rounded-full bg-line"
            >
              <div
                className="h-full rounded-full bg-blue"
                style={{ width: `${total ? (count / total) * 100 : 0}%` }}
              />
            </div>
            <span className="w-8 text-right text-ink">{count}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

function Industries({ industries }: { industries: IndustryResult[] }) {
  // Only industries someone answered with; most responses first (a stable
  // sort keeps the backend's choice order for ties).
  const rows = industries
    .filter((industry) => industry.count > 0)
    .sort((a, b) => b.count - a.count);

  return (
    <Card>
      <h2 className="text-base font-semibold text-ink">By industry</h2>
      <p className="mt-1 text-xs text-slate">
        Averages need at least 3 responses, so a small industry&apos;s ratings
        can&apos;t be traced to one person.
      </p>
      <div className="mt-4">
        <Table>
          <thead>
            <tr>
              <Th>Industry</Th>
              <Th>Responses</Th>
              <Th>Avg. preparedness</Th>
              <Th>Avg. helpfulness</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((industry) => (
              <tr key={industry.code}>
                <Td>{industry.label}</Td>
                <Td>{industry.count}</Td>
                <AverageCell value={industry.preparedness_average} />
                <AverageCell value={industry.platform_helpfulness_average} />
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </Card>
  );
}

function AverageCell({ value }: { value: number | null }) {
  const shown = average(value);
  return shown === null ? (
    <Td className="text-slate">Too few responses</Td>
  ) : (
    <Td>{shown}</Td>
  );
}

function CountTable({
  heading,
  rows,
}: {
  heading: string;
  rows: { key: string; label: string; count: number }[];
}) {
  if (rows.length === 0) {
    return <p className="mt-4 text-sm text-slate">None yet.</p>;
  }
  return (
    <div className="mt-4">
      <Table>
        <thead>
          <tr>
            <Th>{heading}</Th>
            <Th>Alumni</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <Td>{row.label}</Td>
              <Td>{row.count}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
