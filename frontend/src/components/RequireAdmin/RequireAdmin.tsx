import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import Navbar from "../Navbar/Navbar";
import { useAdminCheck } from "./useAdminCheck";

// Keeps the admin pages to admins: anyone else signed in is sent to their
// profile, and someone not logged in to the login page.
//
// This only hides pages - the admin API refuses non-admins itself (IsAdmin),
// so it is not a security control. That's also why an account that can't be
// checked (the server unreachable, say) is let through, like
// RequireVerifiedEmail: the page's own requests will report the problem.
export default function RequireAdmin({ children }: { children: ReactNode }) {
  const check = useAdminCheck();

  if (check === "admin" || check === "unknown") {
    return <>{children}</>;
  }
  // Same loading shell as RequireVerifiedEmail, so redirects don't flash.
  return (
    <div className="min-h-screen bg-canvas font-sans text-sm text-slate">
      <Navbar />
      <p className="mx-auto max-w-6xl px-8 pt-2">Loading...</p>
      {check === "logged-out" && <Navigate to="/login" replace />}
      {check === "not-admin" && <Navigate to="/profile" replace />}
    </div>
  );
}
