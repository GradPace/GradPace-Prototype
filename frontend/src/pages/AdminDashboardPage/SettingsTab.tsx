import { useEffect, useState } from "react";
import {
  getSettings,
  updateSettings,
  type SiteSettings,
} from "../../lib/api/admin";
import { Card } from "./ui";

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

// Site-wide switches (GET/PATCH /api/auth/admin/settings/). Each change saves
// straight away.
export default function SettingsTab() {
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let stale = false;
    getSettings()
      .then((loaded) => !stale && setSettings(loaded))
      .catch((err) => !stale && setError(errorMessage(err)));
    return () => {
      stale = true;
    };
  }, []);

  async function setRequired(required: boolean) {
    if (
      !required &&
      !window.confirm(
        "Turn off email verification? Unverified users will be let straight in.",
      )
    ) {
      return;
    }
    setError(null);
    setSaving(true);
    try {
      setSettings(
        await updateSettings({ require_email_verification: required }),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (!settings) {
    return error ? (
      <p role="alert" className="text-sm text-pink">
        {error}
      </p>
    ) : (
      <p className="text-sm text-slate">Loading settings...</p>
    );
  }

  const required = settings.require_email_verification;
  return (
    <Card>
      <h2 className="text-base font-semibold text-ink">Settings</h2>

      <div className="mt-5 flex items-start justify-between gap-6">
        <div>
          <p id="require-verification" className="text-sm font-medium text-ink">
            Require email verification
          </p>
          <p className="mt-1 max-w-xl text-sm text-slate">
            New users must confirm their email before reaching their profile.
            Turning this off lets unverified users straight in. It doesn&apos;t
            change anyone&apos;s verified status.
          </p>
          {/* Only once someone has changed it: the row is created on first
              read, so updated_at alone doesn't mean anyone chose this. */}
          {settings.updated_by && (
            <p className="mt-2 text-xs text-slate">
              Last changed by {settings.updated_by} on{" "}
              {new Date(settings.updated_at).toLocaleString()}
            </p>
          )}
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={required}
          aria-labelledby="require-verification"
          disabled={saving}
          onClick={() => setRequired(!required)}
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
            required ? "bg-blue" : "bg-line"
          }`}
        >
          <span
            className={`inline-block h-5 w-5 rounded-full bg-white transition-transform ${
              required ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-4 text-sm text-pink">
          {error}
        </p>
      )}
    </Card>
  );
}
