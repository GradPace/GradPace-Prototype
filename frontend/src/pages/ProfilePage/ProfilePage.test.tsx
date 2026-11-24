import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ProfilePage from "./ProfilePage";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigateMock };
});

const READINESS = {
  overall_readiness_score: 50.07,
  skills: {
    points: 20.91,
    out_of: 50,
    groups: [
      {
        key: "language",
        name: "Main language",
        points: 8.62,
        out_of: 8.62,
        best_tool: "Java",
        level: "Project ready",
      },
      {
        key: "cloud",
        name: "Cloud",
        points: 0,
        out_of: 4.31,
        best_tool: null,
        level: null,
      },
    ],
  },
  courses: {
    points: 29.17,
    out_of: 50,
    list: [
      { code: "CS 151", name: "Intro", taken: true },
      { code: "CS 450", name: "Database Concepts", taken: false },
    ],
  },
  certificates: { bonus: 5, max_bonus: 10, counted: ["CompTIA Security+"] },
  benchmark: { location: "Norfolk, VA", postings_used: 21 },
};

// The profile request gets `response`; the demo readiness request gets
// READINESS when the profile exists, otherwise the same error.
function stubProfileResponse(response: {
  ok: boolean;
  status: number;
  body: unknown;
}) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      const body =
        url.includes("/api/benchmark/demo/me/") && response.ok
          ? READINESS
          : response.body;
      return Promise.resolve({
        ok: response.ok,
        status: response.status,
        json: () => Promise.resolve(body),
      });
    }),
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    navigateMock.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the fetched profile fields", async () => {
    stubProfileResponse({
      ok: true,
      status: 200,
      body: {
        first_name: "Ada",
        last_name: "Lovelace",
        student_id: "S123",
        uni: "State University",
        major: "Computer Science",
        location: "Remote",
      },
    });

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { level: 2, name: "Ada Lovelace" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Welcome back, Ada")).toBeInTheDocument();
    expect(screen.getByText("ID S123")).toBeInTheDocument();
    expect(screen.getByText("State University")).toBeInTheDocument();
    expect(screen.getByText("Computer Science")).toBeInTheDocument();
    expect(screen.getByText("Remote")).toBeInTheDocument();
  });

  it("shows the demo readiness score and what makes it up", async () => {
    stubProfileResponse({
      ok: true,
      status: 200,
      body: { first_name: "Ada", last_name: "Lovelace", readiness_score: 12 },
    });

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    );

    // The gauge shows the demo score, not the profile's stored readiness_score
    expect(await screen.findByText("50")).toBeInTheDocument();
    expect(screen.getByText("Getting started")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Skills" })).toHaveAttribute(
      "aria-valuenow",
      "42",
    );
    expect(screen.getByText("1 of 2 taken")).toBeInTheDocument();
    expect(screen.getByText("CompTIA Security+")).toBeInTheDocument();
    expect(screen.getByText(/based on 21 software developer job postings in norfolk, va/i)).toBeInTheDocument();
    // Removed cards
    expect(screen.queryByText("Graduation status")).not.toBeInTheDocument();
    expect(screen.queryByText("Profile completeness")).not.toBeInTheDocument();
    expect(screen.queryByText("Student record")).not.toBeInTheDocument();
    expect(screen.queryByText("What to work on next")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Update skills & courses" }),
    ).toHaveAttribute("href", "/profileSetup");
  });

  it("shows the skill breakdown in a pop-up", async () => {
    stubProfileResponse({
      ok: true,
      status: 200,
      body: { first_name: "Ada", last_name: "Lovelace" },
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    );

    const open = await screen.findByRole("button", {
      name: "View skill breakdown",
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(open);
    const dialog = screen.getByRole("dialog", { name: "Skill breakdown" });
    expect(within(dialog).getByText("Java - Project ready")).toBeInTheDocument();
    expect(within(dialog).getByText("Not started")).toBeInTheDocument();
    expect(
      within(dialog).getByRole("progressbar", { name: "Cloud" }),
    ).toHaveAttribute("aria-valuenow", "0");

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(open);
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("redirects to /profileSetup when no profile exists yet (404)", async () => {
    stubProfileResponse({ ok: false, status: 404, body: null });

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    );

    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith("/profileSetup", {
        replace: true,
      }),
    );
  });

  it("redirects to /login when unauthenticated (401)", async () => {
    stubProfileResponse({ ok: false, status: 401, body: null });

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    );

    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith("/login", { replace: true }),
    );
  });
});
