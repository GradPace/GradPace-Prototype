import { useEffect, useState } from "react";
import {
  listUsers,
  setUserActive,
  USERS_PAGE_SIZE,
  type AdminUser,
  type Page,
} from "../../lib/api/admin";
import { knownMe } from "../../lib/api/me";
import { Badge, Button, Card, Table, Td, Th } from "./ui";

const SEARCH_DEBOUNCE_MS = 300;

// What the list was last loaded for, so "loading" is simply "the result is
// for some other search/page" - no separate flag to keep in step.
type Loaded =
  | { key: string; page: Page<AdminUser> }
  | { key: string; error: string };

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

function fullName(user: AdminUser): string {
  return `${user.first_name} ${user.last_name}`.trim() || "(no name)";
}

function roleLabel(role: string | null): string {
  return role ? role.charAt(0).toUpperCase() + role.slice(1) : "No role";
}

function isSelf(user: AdminUser): boolean {
  // The page guards fetched the account just before (knownMe). If that's
  // ever missing, the backend still refuses self-deactivation with a 400.
  const me = knownMe();
  return Boolean(me) && user.email.toLowerCase() === me!.email.toLowerCase();
}

export default function UsersTab() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const key = `${search}|${offset}`;

  // Wait for typing to pause, then search from the first page.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query.trim());
      setOffset(0);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    let stale = false;
    listUsers(search, offset)
      .then((page) => !stale && setLoaded({ key, page }))
      .catch((err) => !stale && setLoaded({ key, error: errorMessage(err) }));
    return () => {
      stale = true;
    };
  }, [key, search, offset]);

  async function toggleActive(user: AdminUser) {
    const activate = !user.is_active;
    if (
      !activate &&
      !window.confirm(
        `Deactivate ${user.email}? They'll be signed out everywhere.`,
      )
    ) {
      return;
    }
    setActionError(null);
    setBusyId(user.id);
    try {
      const updated = await setUserActive(user.id, activate);
      setLoaded((current) =>
        current && "page" in current
          ? {
              ...current,
              page: {
                ...current.page,
                results: current.page.results.map((row) =>
                  row.id === updated.id ? updated : row,
                ),
              },
            }
          : current,
      );
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  const current = loaded?.key === key ? loaded : null;

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-ink">Users</h2>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by email"
          aria-label="Search users by email"
          className="w-full max-w-xs rounded-md border border-line bg-canvas px-3 py-2 text-sm text-ink placeholder:text-slate focus:border-blue focus:outline-none"
        />
      </div>

      {actionError && (
        <p role="alert" className="mt-4 text-sm text-pink">
          {actionError}
        </p>
      )}

      <div className="mt-5">
        {!current && <p className="text-sm text-slate">Loading users...</p>}

        {current && "error" in current && (
          <p role="alert" className="text-sm text-pink">
            {current.error}
          </p>
        )}

        {current && "page" in current && current.page.results.length === 0 && (
          <p className="text-sm text-slate">
            {search ? `No users match "${search}".` : "No users yet."}
          </p>
        )}

        {current && "page" in current && current.page.results.length > 0 && (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Name</Th>
                  <Th>Email</Th>
                  <Th>Role</Th>
                  <Th>Joined</Th>
                  <Th>Status</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {current.page.results.map((user) => {
                  const self = isSelf(user);
                  return (
                    <tr key={user.id}>
                      <Td>{fullName(user)}</Td>
                      <Td className="text-slate">{user.email}</Td>
                      <Td>
                        <Badge>{roleLabel(user.role)}</Badge>
                      </Td>
                      <Td className="whitespace-nowrap text-slate">
                        {new Date(user.date_joined).toLocaleDateString()}
                      </Td>
                      <Td>
                        <Badge tone={user.is_active ? "active" : "inactive"}>
                          {user.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </Td>
                      <Td className="text-right">
                        <Button
                          onClick={() => toggleActive(user)}
                          disabled={self || busyId === user.id}
                          title={
                            self
                              ? "You can't deactivate your own account"
                              : undefined
                          }
                          aria-label={`${user.is_active ? "Deactivate" : "Reactivate"} ${user.email}`}
                        >
                          {user.is_active ? "Deactivate" : "Reactivate"}
                        </Button>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>

            <Pagination
              offset={offset}
              shown={current.page.results.length}
              count={current.page.count}
              onChange={setOffset}
            />
          </>
        )}
      </div>
    </Card>
  );
}

function Pagination({
  offset,
  shown,
  count,
  onChange,
}: {
  offset: number;
  shown: number;
  count: number;
  onChange: (offset: number) => void;
}) {
  return (
    <div className="mt-4 flex items-center justify-between gap-4 text-sm text-slate">
      <p>
        Showing {offset + 1}–{offset + shown} of {count}
      </p>
      <div className="flex gap-2">
        <Button
          onClick={() => onChange(Math.max(0, offset - USERS_PAGE_SIZE))}
          disabled={offset === 0}
        >
          Prev
        </Button>
        <Button
          onClick={() => onChange(offset + USERS_PAGE_SIZE)}
          disabled={offset + USERS_PAGE_SIZE >= count}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
