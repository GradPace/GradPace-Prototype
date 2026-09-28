import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { ApiError, apiGet } from "../../lib/api/api";
// Put your icon file at this path (or change it to match yours)
import profileIcon from "../../assets/profile-icon.png";

type StudentProfile = {
  first_name: string;
  last_name: string;
  student_id: string;
  uni: string;
  major: string;
  location: string | null;
};

export default function ProfilePage() {
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

      <main className="mx-auto flex max-w-6xl justify-center px-8 py-24">
        <div className="w-full max-w-xl rounded-2xl border border-line bg-surface p-10">
          {error && <p className="text-sm text-pink">{error}</p>}

          {!profile && !error && (
            <p className="text-sm text-slate">Loading...</p>
          )}

          {profile && (
            <>
              <div className="flex items-center gap-5">
                <img
                  src={profileIcon}
                  alt="Profile"
                  className="h-20 w-20 rounded-full border border-line object-cover"
                />
                <h1 className="text-4xl font-medium text-ink">
                  {profile.first_name} {profile.last_name}
                </h1>
              </div>

              <dl className="mt-8 grid gap-4">
                <ProfileField label="Student ID" value={profile.student_id} />
                <ProfileField label="University" value={profile.uni} />
                <ProfileField label="Major" value={profile.major} />
                <ProfileField label="Location" value={profile.location} />
              </dl>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function ProfileField({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="flex flex-col gap-1 border-b border-line pb-3">
      <dt className="text-sm font-medium text-slate">{label}</dt>
      <dd className="text-base text-ink">{value || "—"}</dd>
    </div>
  );
}
