import { useState } from "react";
import Navbar from "../../components/Navbar/Navbar";
import DataQualityTab from "./DataQualityTab";
import SettingsTab from "./SettingsTab";
import SurveyResultsTab from "./SurveyResultsTab";
import UsersTab from "./UsersTab";

// One entry per tab - add a tab by adding a line.
const TABS = [
  { id: "users", label: "Users", Panel: UsersTab },
  { id: "data-quality", label: "Data quality", Panel: DataQualityTab },
  { id: "survey-results", label: "Survey results", Panel: SurveyResultsTab },
  { id: "settings", label: "Settings", Panel: SettingsTab },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function AdminDashboardPage() {
  const [activeId, setActiveId] = useState<TabId>(TABS[0].id);
  const active = TABS.find((tab) => tab.id === activeId) ?? TABS[0];

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto max-w-6xl px-8 pt-2 pb-12">
        <h1 className="text-3xl font-semibold text-ink">Admin dashboard</h1>

        <div
          role="tablist"
          aria-label="Admin sections"
          className="mt-6 flex gap-6 border-b border-line"
        >
          {TABS.map((tab) => {
            const selected = tab.id === active.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={selected}
                aria-controls={`panel-${tab.id}`}
                onClick={() => setActiveId(tab.id)}
                className={`-mb-px border-b-2 pb-3 text-sm font-medium transition-colors ${
                  selected
                    ? "border-blue text-ink"
                    : "border-transparent text-slate hover:text-ink"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Only the open tab is mounted, so each loads its data when opened. */}
        <div
          role="tabpanel"
          id={`panel-${active.id}`}
          aria-labelledby={`tab-${active.id}`}
          className="mt-6"
        >
          <active.Panel />
        </div>
      </main>
    </div>
  );
}
