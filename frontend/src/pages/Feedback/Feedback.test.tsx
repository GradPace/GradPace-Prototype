import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Feedback from "./Feedback";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigateMock };
});

const READINESS = {
  overall_readiness_score: 50.07,
  skills: {
    groups: [
      {
        key: "language",
        name: "Main language",
        points: 2.15,
        out_of: 8.62,
        best_tool: "Python",
        level: "Learning",
        options: [{ name: "Python", label: "Python" }],
      },
      {
        key: "version_control",
        name: "Version control",
        points: 4.43,
        out_of: 7.38,
        best_tool: "Git",
        level: "Practicing",
        options: [{ name: "Git", label: "Git" }],
      },
      {
        key: "os",
        name: "Operating systems",
        points: 2.6,
        out_of: 2.6,
        best_tool: "Linux",
        level: "Project ready",
        options: [{ name: "Linux", label: "Linux" }],
      },
    ],
  },
  courses: {
    list: [
      { code: "CS 151", name: "Intro", taken: true, points: 4.17 },
      { code: "CS 450", name: "Database Concepts", taken: false, points: 4.17 },
    ],
  },
  certificates: {
    bonus: 5,
    max_bonus: 10,
    counted: ["CompTIA Security+"],
    options: ["CompTIA Security+", "AWS Certified Cloud Practitioner"],
  },
  next_steps: [
    { kind: "skill", name: "Main language", points_available: 6.47 },
    { kind: "course", name: "CS 450 Database Concepts", points_available: 4.17 },
  ],
};

function stubResponse(ok: boolean, status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok,
      status,
      json: () => Promise.resolve(body),
    }),
  );
}

function renderPage() {
  render(
    <MemoryRouter>
      <Feedback />
    </MemoryRouter>,
  );
}

describe("Feedback", () => {
  beforeEach(() => {
    navigateMock.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists the next steps, courses and certificates still to complete", async () => {
    stubResponse(true, 200, READINESS);
    renderPage();

    expect(await screen.findByText(/out of 100/i)).toBeInTheDocument();
    expect(screen.getByText("Improve Main language")).toBeInTheDocument();
    expect(screen.getByText("Take CS 450 Database Concepts")).toBeInTheDocument();
    expect(screen.getByText("Database Concepts")).toBeInTheDocument();
    expect(screen.queryByText("CS 151")).not.toBeInTheDocument();
    expect(screen.getByText("AWS Certified Cloud Practitioner")).toBeInTheDocument();
    // Project ready groups have nothing left to improve
    expect(screen.queryByText("Operating systems")).not.toBeInTheDocument();
  });

  it("links free resources only for skills still being learned", async () => {
    stubResponse(true, 200, READINESS);
    renderPage();

    expect(await screen.findByText(/you're learning python/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "freeCodeCamp" })).toHaveAttribute(
      "href",
      "https://www.freecodecamp.org/learn",
    );
    expect(screen.getByText(/build a project with it/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "GitHub Skills" }),
    ).not.toBeInTheDocument();
  });

  it("redirects to login when the token is missing or expired", async () => {
    stubResponse(false, 401, { detail: "Not authenticated" });
    renderPage();

    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith("/login", { replace: true }),
    );
  });

  it("redirects to profile setup when there is no profile yet", async () => {
    stubResponse(false, 404, null);
    renderPage();

    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith("/profileSetup", {
        replace: true,
      }),
    );
  });
});
