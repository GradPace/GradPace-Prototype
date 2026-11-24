import { useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import Navbar from "../Navbar/Navbar";
import { ApiError, apiGet } from "../../lib/api/api";
import { canSkipVerification, rememberMe, type Me } from "../../lib/api/me";

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
    apiGet<Me>("/api/auth/me/")
      .then((me) => {
        rememberMe(me);
        setState(canSkipVerification(me) ? "verified" : "unverified");
      })
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

  // Navigate renders nothing until the route changes a moment later, which
  // showed as a blank frame between pages. So the loading shell (with the
  // navigation bar) stays up for the checking state and for both redirects.
  if (state !== "verified") {
    return (
      <div className="min-h-screen bg-canvas font-sans text-sm text-slate">
        <Navbar />
        <p className="mx-auto max-w-6xl px-8 pt-2">Loading...</p>
        {state === "logged-out" && <Navigate to="/login" replace />}
        {state === "unverified" && <Navigate to="/verify-your-email" replace />}
      </div>
    );
  }
  return <>{children}</>;
}
