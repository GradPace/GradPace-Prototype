import { useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { ApiError, apiGet } from "../../lib/api/api";

type State = "checking" | "verified" | "unverified" | "logged-out";

// Keeps a signed-in user whose email isn't verified yet out of the pages
// inside it (profile setup, profile): they are sent to /verify-your-email
// instead, which says to open the emailed link and can send it again.
//
// This only hides pages. The API doesn't refuse an unverified user (they can
// still log in, as the product spec says), so it is not a security control.
export default function RequireVerifiedEmail({
  children,
}: {
  children: ReactNode;
}) {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    apiGet<{ email_verified: boolean }>("/api/auth/me/")
      .then((me) => setState(me.email_verified ? "verified" : "unverified"))
      .catch((err) =>
        // Not logged in (or the login ran out): the login page. Anything else
        // - the server unreachable, say - isn't a reason to lock anyone out;
        // the page's own requests will report the problem.
        setState(
          err instanceof ApiError && err.status === 401
            ? "logged-out"
            : "verified",
        ),
      );
  }, []);

  if (state === "checking") {
    return (
      <div className="min-h-screen bg-canvas font-sans text-sm text-slate">
        <p className="p-8">Loading...</p>
      </div>
    );
  }
  if (state === "logged-out") return <Navigate to="/login" replace />;
  if (state === "unverified") {
    return <Navigate to="/verify-your-email" replace />;
  }
  return <>{children}</>;
}
