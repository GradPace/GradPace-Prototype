import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import EventsPage from "./EventsPage";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigateMock };
});

const AI_EVENT = {
  id: "ai-horizons",
  title: "AI Horizons",
  date: "2026-12-05",
  time: "10:00 AM EST",
  duration: "4 hours",
  location: "Norfolk, VA",
  venue: "Harborfront Conference Hall",
  cost: "Free",
  format: "In person",
  focus: "Artificial Intelligence",
  audience: "Students",
  prerequisites: "", // blank fields are left out of the details
  registration: "Free online registration",
  speakers: "Industry engineers",
  description: "Talks and labs on machine learning.",
  agenda: ["10:00 Training models", "1:00 Bias lab"],
  key_topics: ["Neural networks"],
};

const CLOUD_EVENT = {
  ...AI_EVENT,
  id: "cloud-night",
  title: "Cloud Night",
  date: "2026-12-12",
  location: "Virginia Beach, VA",
  description: "An evening of AWS demos.",
};

const NO_EVENTS_404 = {
  status: 404,
  body: { detail: "No upcoming Hampton Roads events." },
};

const EMPTY_CHAT = { exchanges: [], chats_remaining: 3, max_chats: 3 };

type Reply = { status: number; body: unknown };

// Answers each API request from `routes`. Endpoints a test doesn't care
// about get defaults: two events, no recommendation, an empty chat.
function stubApi(
  routes: {
    events?: Reply;
    recommendation?: Reply;
    chat?: Reply;
    ask?: Reply | Promise<Reply>;
  } = {},
) {
  const fetchMock = vi
    .fn()
    .mockImplementation(async (url: string, init?: RequestInit) => {
      let reply: Reply;
      if (url.includes("/chat/") && init?.method === "POST") {
        reply = await (routes.ask ?? { status: 200, body: EMPTY_CHAT });
      } else if (url.includes("/chat/")) {
        reply = routes.chat ?? { status: 200, body: EMPTY_CHAT };
      } else if (url.includes("/events/recommendation/")) {
        reply = routes.recommendation ?? NO_EVENTS_404;
      } else if (url.includes("/api/intelligence/events/")) {
        reply = routes.events ?? {
          status: 200,
          body: [AI_EVENT, CLOUD_EVENT],
        };
      } else {
        reply = { status: 404, body: null };
      }
      return {
        ok: reply.status >= 200 && reply.status < 300,
        status: reply.status,
        json: () => Promise.resolve(reply.body),
        text: () => Promise.resolve(JSON.stringify(reply.body)),
      };
    });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderPage() {
  return render(
    <MemoryRouter>
      <EventsPage />
    </MemoryRouter>,
  );
}

// The card in "All upcoming events" for the event with this title.
async function listCard(title: string) {
  const heading = await screen.findByRole("heading", { level: 2, name: title });
  return heading.closest("li") as HTMLElement;
}

// Opens a card's details, which also loads its chat.
async function openDetails(card: HTMLElement) {
  await userEvent.click(within(card).getByRole("button", { name: /view details/i }));
}

describe("EventsPage", () => {
  beforeEach(() => {
    navigateMock.mockClear();
    localStorage.clear();
    localStorage.setItem("access", "my-token");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("event list", () => {
    it("lists the upcoming events", async () => {
      stubApi();
      renderPage();

      const card = await listCard("AI Horizons");
      expect(
        within(card).getByText("2026-12-05 · 10:00 AM EST · Norfolk, VA"),
      ).toBeInTheDocument();
      expect(
        within(card).getByText("Talks and labs on machine learning."),
      ).toBeInTheDocument();
      expect(await listCard("Cloud Night")).toBeInTheDocument();
    });

    it("says so when there are no upcoming events", async () => {
      stubApi({ events: { status: 200, body: [] } });
      renderPage();

      expect(await screen.findByText("No upcoming events.")).toBeInTheDocument();
    });

    it("shows the error when the events can't be loaded", async () => {
      stubApi({ events: { status: 500, body: { detail: "Server error" } } });
      renderPage();

      expect(await screen.findByText("Server error")).toBeInTheDocument();
    });

    it("sends a logged-out user to the login page", async () => {
      stubApi({
        events: { status: 401, body: { detail: "Not authenticated" } },
        recommendation: { status: 401, body: { detail: "Not authenticated" } },
      });
      renderPage();

      await vi.waitFor(() =>
        expect(navigateMock).toHaveBeenCalledWith("/login", { replace: true }),
      );
    });
  });

  describe("recommended event", () => {
    it("shows the pick, why it fits and how far away it is", async () => {
      stubApi({
        recommendation: {
          status: 200,
          body: {
            event: CLOUD_EVENT,
            reason: "It covers AWS, one of your skill gaps.",
            reason_source: "ai",
            distance_miles: 4.2,
            chats_remaining: 3,
          },
        },
      });
      renderPage();

      const label = await screen.findByText("Recommended for you");
      const card = label.closest("section") as HTMLElement;
      expect(within(card).getByRole("heading", { name: "Cloud Night" })).toBeInTheDocument();
      expect(
        within(card).getByText("It covers AWS, one of your skill gaps."),
      ).toBeInTheDocument();
      expect(within(card).getByText(/4\.2 mi away/)).toBeInTheDocument();
      expect(within(card).queryByText(/AI advisor is unavailable/)).not.toBeInTheDocument();
    });

    it("notes when the AI was down and the reason is a template", async () => {
      stubApi({
        recommendation: {
          status: 200,
          body: {
            event: CLOUD_EVENT,
            reason: "It's the best upcoming match for you on timing and location.",
            reason_source: "fallback",
            distance_miles: null,
            chats_remaining: 3,
          },
        },
      });
      renderPage();

      const label = await screen.findByText("Recommended for you");
      const card = label.closest("section") as HTMLElement;
      expect(within(card).getByText(/AI advisor is unavailable/)).toBeInTheDocument();
      expect(within(card).queryByText(/mi away/)).not.toBeInTheDocument();
    });

    it("sends a student without a profile to profile setup", async () => {
      stubApi({
        recommendation: { status: 404, body: { detail: "No student profile yet." } },
      });
      renderPage();

      await vi.waitFor(() =>
        expect(navigateMock).toHaveBeenCalledWith("/profileSetup", { replace: true }),
      );
    });

    it("shows no card, and doesn't redirect, when no events are left", async () => {
      stubApi({ events: { status: 200, body: [] } });
      renderPage();

      await screen.findByText("No upcoming events.");
      expect(screen.queryByText("Finding an event for you...")).not.toBeInTheDocument();
      expect(screen.queryByText("Recommended for you")).not.toBeInTheDocument();
      expect(navigateMock).not.toHaveBeenCalled();
    });

    it("shows the backend's message when the recommendation fails", async () => {
      stubApi({
        recommendation: {
          status: 503,
          body: { detail: "The AI model is unavailable right now." },
        },
      });
      renderPage();

      expect(
        await screen.findByText("The AI model is unavailable right now."),
      ).toBeInTheDocument();
    });
  });

  describe("event details", () => {
    it("opens and closes the full details", async () => {
      stubApi();
      renderPage();
      const card = await listCard("AI Horizons");

      expect(within(card).queryByText("Harborfront Conference Hall")).not.toBeInTheDocument();

      await openDetails(card);
      const toggle = within(card).getByRole("button", { name: /hide details/i });
      expect(toggle).toHaveAttribute("aria-expanded", "true");
      expect(within(card).getByText("Venue")).toBeInTheDocument();
      expect(within(card).getByText("Harborfront Conference Hall")).toBeInTheDocument();
      expect(within(card).getByText("10:00 Training models")).toBeInTheDocument();
      expect(within(card).getByText("Neural networks")).toBeInTheDocument();
      // Blank fields aren't listed
      expect(within(card).queryByText("Prerequisites")).not.toBeInTheDocument();

      await userEvent.click(toggle);
      expect(within(card).queryByText("Harborfront Conference Hall")).not.toBeInTheDocument();
      expect(within(card).getByRole("button", { name: /view details/i })).toHaveAttribute(
        "aria-expanded",
        "false",
      );
    });
  });

  describe("event chat", () => {
    it("loads only when the details are opened", async () => {
      const fetchMock = stubApi();
      renderPage();
      const card = await listCard("AI Horizons");

      const chatCalls = () =>
        fetchMock.mock.calls.filter(([url]) => (url as string).includes("/chat/"));
      expect(chatCalls()).toHaveLength(0);

      await openDetails(card);
      expect(await within(card).findByText("3 of 3 questions left")).toBeInTheDocument();
      expect(chatCalls()).toHaveLength(1);
      expect(chatCalls()[0][0]).toContain("/api/intelligence/events/ai-horizons/chat/");
    });

    it("shows earlier questions and labels free fact answers", async () => {
      stubApi({
        chat: {
          status: 200,
          body: {
            exchanges: [
              { question: "How much is it?", answer: "Free.", source: "facts" },
              { question: "Good for beginners?", answer: "Yes.", source: "model" },
            ],
            chats_remaining: 2,
            max_chats: 3,
          },
        },
      });
      renderPage();
      const card = await listCard("AI Horizons");
      await openDetails(card);

      expect(await within(card).findByText("How much is it?")).toBeInTheDocument();
      expect(within(card).getByText("Free.")).toBeInTheDocument();
      expect(within(card).getByText("Yes.")).toBeInTheDocument();
      expect(within(card).getAllByText(/doesn't use a question/)).toHaveLength(1);
      expect(within(card).getByText("2 of 3 questions left")).toBeInTheDocument();
    });

    it("sends a question and shows the answer", async () => {
      let answer!: (reply: Reply) => void;
      const ask = new Promise<Reply>((resolve) => {
        answer = resolve;
      });
      const fetchMock = stubApi({ ask });
      const user = userEvent.setup();
      renderPage();
      const card = await listCard("AI Horizons");
      await openDetails(card);

      const input = await within(card).findByLabelText("Your question");
      const askButton = within(card).getByRole("button", { name: "Ask" });
      expect(askButton).toBeDisabled(); // blank box

      await user.type(input, "  Is lunch provided?  ");
      await user.click(askButton);

      // While waiting: the question shows with "Thinking...", and the form is locked
      expect(await within(card).findByText("Thinking...")).toBeInTheDocument();
      expect(within(card).getByText("Is lunch provided?")).toBeInTheDocument();
      expect(input).toBeDisabled();
      expect(within(card).getByRole("button", { name: "Sending..." })).toBeDisabled();

      const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
      expect(post![0]).toContain("/api/intelligence/events/ai-horizons/chat/");
      expect(post![1].headers).toMatchObject({ Authorization: "Bearer my-token" });
      expect(JSON.parse(post![1].body as string)).toEqual({
        question: "Is lunch provided?", // trimmed
      });

      answer({
        status: 200,
        body: {
          exchanges: [
            { question: "Is lunch provided?", answer: "Yes, lunch is included.", source: "model" },
          ],
          chats_remaining: 2,
          max_chats: 3,
        },
      });

      expect(await within(card).findByText("Yes, lunch is included.")).toBeInTheDocument();
      expect(within(card).queryByText("Thinking...")).not.toBeInTheDocument();
      expect(within(card).getByText("2 of 3 questions left")).toBeInTheDocument();
      expect(input).toHaveValue("");
      expect(input).toBeEnabled();
    });

    it("shows the limit message and keeps the question to retry", async () => {
      stubApi({
        ask: {
          status: 429,
          body: {
            detail: "You have used all 3 questions for this event.",
            code: "chat_limit_reached",
          },
        },
      });
      const user = userEvent.setup();
      renderPage();
      const card = await listCard("AI Horizons");
      await openDetails(card);

      const input = await within(card).findByLabelText("Your question");
      await user.type(input, "Who is speaking?");
      await user.click(within(card).getByRole("button", { name: "Ask" }));

      // Only the detail - not the error code tacked on
      expect(
        await within(card).findByText("You have used all 3 questions for this event."),
      ).toBeInTheDocument();
      expect(within(card).queryByText(/chat_limit_reached/)).not.toBeInTheDocument();
      expect(input).toHaveValue("Who is speaking?");
    });

    it("keeps the box usable for facts once every question is used", async () => {
      stubApi({
        chat: { status: 200, body: { exchanges: [], chats_remaining: 0, max_chats: 3 } },
      });
      renderPage();
      const card = await listCard("AI Horizons");
      await openDetails(card);

      expect(await within(card).findByText(/used all your questions/)).toBeInTheDocument();
      expect(within(card).getByText("0 of 3 questions left")).toBeInTheDocument();
      expect(within(card).getByLabelText("Your question")).toBeEnabled();
    });

    it("shows the error when the chat can't be loaded", async () => {
      stubApi({ chat: { status: 404, body: { detail: "Not found." } } });
      renderPage();
      const card = await listCard("AI Horizons");
      await openDetails(card);

      expect(await within(card).findByText("Not found.")).toBeInTheDocument();
      expect(within(card).queryByLabelText("Your question")).not.toBeInTheDocument();
    });
  });
});
