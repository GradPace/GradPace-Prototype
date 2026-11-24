import { Card } from "./ui";

// Placeholder - built in the next GP-62 step (GET
// /api/intelligence/admin/data-health/, lib/api/admin.ts getDataHealth).
export default function DataQualityTab() {
  return (
    <Card>
      <h2 className="text-base font-semibold text-ink">Data quality</h2>
      <p className="mt-2 text-sm text-slate">
        Job catalog and student location checks are coming next.
      </p>
    </Card>
  );
}
