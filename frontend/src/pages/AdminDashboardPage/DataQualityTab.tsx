import { useEffect, useState } from "react";
import {
  getDataHealth,
  type DataHealth,
  type OccupationHealth,
  type SourceTotals,
  type StudentLocations,
} from "../../lib/api/admin";
import { Badge, Card, Stat, Table, Td, Th } from "./ui";

type Loaded = { data: DataHealth } | { error: string };

const wage = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function isFlagged(job: OccupationHealth): boolean {
  return job.few_postings || job.missing_wage || job.no_skills;
}

// Catalog health (GET /api/intelligence/admin/data-health/): totals, gaps per
// occupation, and how many student locations event distance can use.
export default function DataQualityTab() {
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    let stale = false;
    getDataHealth()
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
    return <p className="text-sm text-slate">Loading data quality...</p>;
  }
  if ("error" in loaded) {
    return (
      <p role="alert" className="text-sm text-pink">
        {loaded.error}
      </p>
    );
  }

  const { totals, catalog_updated_at, occupations, student_locations } =
    loaded.data;
  return (
    <div className="flex flex-col gap-6">
      <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Jobs" value={totals.jobs.total}>
          <SourceBreakdown totals={totals.jobs} />
        </Stat>
        <Stat label="Skills" value={totals.skills.total} />
        <Stat label="Postings" value={totals.postings.total}>
          <SourceBreakdown totals={totals.postings} />
        </Stat>
        <Stat
          label="Catalog last seeded or edited"
          value={
            <span className="text-base">
              {catalog_updated_at
                ? new Date(catalog_updated_at).toLocaleString()
                : "Never"}
            </span>
          }
        />
      </section>

      <Occupations
        occupations={occupations}
        catalogEmpty={totals.jobs.total === 0}
      />
      <Locations locations={student_locations} />
    </div>
  );
}

// Every source the backend counted, in its order (model choices first, then
// anything unexpected, such as a hand-made row or 'unknown' for blank).
function SourceBreakdown({ totals }: { totals: SourceTotals }) {
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1">
      {Object.entries(totals.by_source).map(([source, count]) => (
        <li key={source}>
          {source} {count}
        </li>
      ))}
    </ul>
  );
}

function Occupations({
  occupations,
  catalogEmpty,
}: {
  occupations: OccupationHealth[];
  catalogEmpty: boolean;
}) {
  const [onlyFlagged, setOnlyFlagged] = useState(false);

  const flagged = occupations.filter(isFlagged);
  // Flagged first; each group keeps the backend's order (soc_code, source).
  const rows = onlyFlagged
    ? flagged
    : [...flagged, ...occupations.filter((job) => !isFlagged(job))];

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-ink">Occupations</h2>
        {!catalogEmpty && (
          <label className="flex items-center gap-2 text-sm text-slate">
            <input
              type="checkbox"
              checked={onlyFlagged}
              onChange={(event) => setOnlyFlagged(event.target.checked)}
              className="accent-blue"
            />
            Show only flagged ({flagged.length} flagged)
          </label>
        )}
      </div>

      <div className="mt-5">
        {catalogEmpty ? (
          <p className="text-sm text-slate">
            The job catalog is empty. Run <code>seed_jobs</code> to load it.
          </p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-slate">No flagged occupations.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>SOC code</Th>
                <Th>Title</Th>
                <Th>Source</Th>
                <Th>Postings</Th>
                <Th>Skills</Th>
                <Th>Median wage</Th>
                <Th>Flags</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((job) => (
                <tr key={`${job.soc_code}|${job.source}`}>
                  <Td className="whitespace-nowrap text-slate">
                    {job.soc_code}
                  </Td>
                  <Td>{job.title}</Td>
                  <Td>
                    <Badge>{job.source || "unknown"}</Badge>
                  </Td>
                  <Td>{job.posting_count}</Td>
                  <Td>{job.skill_count}</Td>
                  <Td className="whitespace-nowrap">
                    {job.median_annual_wage === null
                      ? "—"
                      : wage.format(job.median_annual_wage)}
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      {job.few_postings && (
                        <Badge tone="flag">Few postings</Badge>
                      )}
                      {job.missing_wage && (
                        <Badge tone="flag">Missing wage</Badge>
                      )}
                      {job.no_skills && <Badge tone="flag">No skills</Badge>}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>
    </Card>
  );
}

function Locations({ locations }: { locations: StudentLocations }) {
  const missing = locations.profiles - locations.with_location;

  return (
    <Card>
      <h2 className="text-base font-semibold text-ink">Student locations</h2>
      <p className="mt-1 text-xs text-slate">
        Unrecognized locations can't be used for event distance, so those
        students' event recommendations ignore distance.
      </p>

      {locations.with_location === 0 ? (
        <p className="mt-4 text-sm text-slate">
          No students have saved a location yet.
        </p>
      ) : (
        <p className="mt-4 text-sm text-ink">
          <span className="font-semibold">
            {locations.recognized} of {locations.with_location}
          </span>{" "}
          locations recognized
        </p>
      )}
      <p className="mt-1 text-sm text-slate">
        {missing} {missing === 1 ? "profile has" : "profiles have"} no location
      </p>

      {locations.with_location > 0 &&
        (locations.unrecognized_values.length === 0 ? (
          <p className="mt-4 text-sm text-slate">
            Every saved location is recognized.
          </p>
        ) : (
          <div className="mt-4">
            <Table>
              <thead>
                <tr>
                  <Th>Unrecognized location</Th>
                  <Th>Students</Th>
                </tr>
              </thead>
              <tbody>
                {locations.unrecognized_values.map(({ location, count }) => (
                  <tr key={location}>
                    <Td>{location}</Td>
                    <Td>{count}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        ))}
    </Card>
  );
}
