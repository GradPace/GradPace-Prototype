import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import Navbar from "../Navbar/Navbar";
import { useAdminCheck } from "../RequireAdmin/useAdminCheck";

// The student pages (profile, profile setup) for everyone but admins, who
// are sent to the admin dashboard instead. Admins have no student profile,
// so the profile page would otherwise send them on to student setup - from a
// typed URL or a Profile link shown before their role was known.
//
// Not logged in is left to RequireVerifiedEmail and the page itself, and an
// account that can't be checked is let through.
export default function RedirectAdmin({ children }: { children: ReactNode }) {
  const check = useAdminCheck();

  if (check === "not-admin" || check === "logged-out" || check === "unknown") {
    return <>{children}</>;
  }
  // Same loading shell as RequireVerifiedEmail, so redirects don't flash.
  return (
    <div className="min-h-screen bg-canvas font-sans text-sm text-slate">
      <Navbar />
      <p className="mx-auto max-w-6xl px-8 pt-2">Loading...</p>
      {check === "admin" && <Navigate to="/admin-dashboard" replace />}
    </div>
  );
}
