export type Me = {
  email: string;
  email_verified: boolean;
  role: string | null;
  // The site-wide switch admins set (Settings tab).
  email_verification_required: boolean;
};

// The account details last fetched - by the page guards or at login - kept
// so the next page can use them straight away instead of fetching again or
// starting from a blank "Loading..." card (the Verify your email page still
// re-fetches to refresh them).
let known: Me | null = null;

export function knownMe(): Me | null {
  return known;
}

export function rememberMe(me: Me | null) {
  known = me;
}

// Role names match backend/accounts/roles.py.
export function isAdmin(me: Me | null): boolean {
  return me?.role === "admin";
}

// Whether the user can go past "Verify your email": they've verified, or an
// admin has turned the requirement off. Only an explicit false turns it off,
// so a response without the field keeps verification required.
export function canSkipVerification(me: Me): boolean {
  return me.email_verified || me.email_verification_required === false;
}
