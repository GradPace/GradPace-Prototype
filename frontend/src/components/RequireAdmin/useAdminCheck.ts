import { useEffect, useState } from "react";
import { ApiError, apiGet } from "../../lib/api/api";
import { isAdmin, knownMe, rememberMe, type Me } from "../../lib/api/me";

// "unknown": the account couldn't be checked (the server unreachable, say).
// Each guard decides what that means for its own pages.
export type AdminCheck =
  | "checking"
  | "admin"
  | "not-admin"
  | "logged-out"
  | "unknown";

function fromMe(me: Me): AdminCheck {
  return isAdmin(me) ? "admin" : "not-admin";
}

// Whether the signed-in user is an admin. Inside RequireVerifiedEmail the
// account was fetched a moment ago (knownMe), so that is used rather than
// asking the server again.
export function useAdminCheck(): AdminCheck {
  const [check, setCheck] = useState<AdminCheck>(() => {
    const me = knownMe();
    return me ? fromMe(me) : "checking";
  });

  useEffect(() => {
    if (knownMe()) return;
    apiGet<Me>("/api/auth/me/")
      .then((me) => {
        rememberMe(me);
        setCheck(fromMe(me));
      })
      .catch((err) =>
        setCheck(
          err instanceof ApiError && err.status === 401
            ? "logged-out"
            : "unknown",
        ),
      );
  }, []);

  return check;
}
