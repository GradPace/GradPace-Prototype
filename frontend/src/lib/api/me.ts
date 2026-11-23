export type Me = { email: string; email_verified: boolean };

// The account details RequireVerifiedEmail last fetched, kept so the Verify
// your email page it redirects to can show them straight away instead of
// starting from a blank "Loading..." card (a second flash right after the
// guard's own). The page still re-fetches to refresh them.
let known: Me | null = null;

export function knownMe(): Me | null {
  return known;
}

export function rememberMe(me: Me | null) {
  known = me;
}
