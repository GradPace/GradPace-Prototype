import { useEffect, useId, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { ApiError, apiFetch, apiGet } from "../../lib/api/api";

// GET /api/intelligence/events/ - one upcoming event (EventSerializer)
type Event = {
  id: string; // slug - used in the chat URL
  title: string;
  date: string; // YYYY-MM-DD
  time: string;
  duration: string;
  location: string;
  venue: string;
  cost: string;
  format: string;
  focus: string;
  audience: string;
  prerequisites: string;
  registration: string;
  speakers: string;
  description: string;
  agenda: string[];
  key_topics: string[];
};

// GET /api/intelligence/events/recommendation/ - the one event picked for
// this student (EventRecommendationSerializer)
type Recommendation = {
  event: Event;
  reason: string;
  reason_source: "ai" | "fallback"; // fallback = AI was down, templated reason
  distance_miles: number | null; // null if the profile location isn't found
  chats_remaining: number;
};

// GET/POST /api/intelligence/events/<id>/chat/ (EventChatSerializer)
type ChatExchange = {
  question: string;
  answer: string;
  // Only 'model' answers use up a question. 'facts' = answered straight from
  // the event data, 'unknown' = the details don't say.
  source: "model" | "facts" | "unknown";
};

type ChatState = {
  exchanges: ChatExchange[];
  chats_remaining: number;
  max_chats: number;
};

// The backend's 404 body when the student hasn't set up a profile yet
const NO_PROFILE_DETAIL = "No student profile yet.";

// Matches EventChatRequestSerializer's max_length
const MAX_QUESTION_CHARS = 300;

// The `detail` of an error response - the backend's own message. Used instead
// of err.message, which also tacks on other fields (e.g. the 429's `code`).
function errorDetail(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const data = err.data as { detail?: unknown } | null;
    if (typeof data?.detail === "string") return data.detail;
    return err.message;
  }
  return fallback;
}

export default function EventsPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<Event[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Event[]>("/api/intelligence/events/")
      .then(setEvents)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { replace: true }); // not logged in / token expired
        } else {
          setError(
            err instanceof Error ? err.message : "Could not load events.",
          );
        }
      });
  }, [navigate]);

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto max-w-6xl px-8 pt-2 pb-12">
        <h1 className="text-3xl font-semibold text-ink">Events</h1>
        <p className="mt-1 text-sm text-slate">
          Upcoming career events in Hampton Roads.
        </p>

        <RecommendedEvent />

        <h2 className="mt-10 text-xl font-semibold text-ink">
          All upcoming events
        </h2>
        <div className="mt-4">
          {error && <p className="text-sm text-pink">{error}</p>}

          {!events && !error && (
            <p className="text-sm text-slate">Loading...</p>
          )}

          {events && events.length === 0 && (
            <p className="text-sm text-slate">No upcoming events.</p>
          )}

          {events && events.length > 0 && (
            <ul className="grid gap-6 md:grid-cols-2">
              {events.map((event) => (
                <li
                  key={event.id}
                  className="rounded-2xl border border-line bg-surface p-6"
                >
                  <h2 className="text-lg font-semibold text-ink">
                    {event.title}
                  </h2>
                  <p className="mt-1 text-sm text-slate">
                    {event.date} · {event.time} · {event.location}
                  </p>
                  <p className="mt-3 text-sm text-ink">{event.description}</p>
                  <EventDetails event={event} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

// The event the backend picked for this student, with why it fits them.
// Loads separately from the list - the AI pick can take a few seconds.
function RecommendedEvent() {
  const navigate = useNavigate();
  const [recommendation, setRecommendation] = useState<Recommendation | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Recommendation>("/api/intelligence/events/recommendation/")
      .then(setRecommendation)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { replace: true });
        } else if (err instanceof ApiError && err.status === 404) {
          if (err.message === NO_PROFILE_DETAIL) {
            navigate("/profileSetup", { replace: true }); // no profile yet
          }
          // Otherwise no upcoming events - the list below says so.
        } else {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load your recommended event.",
          );
        }
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading) {
    return (
      <p className="mt-8 text-sm text-slate">Finding an event for you...</p>
    );
  }
  if (error) {
    return <p className="mt-8 text-sm text-pink">{error}</p>;
  }
  if (!recommendation) return null;

  const { event, reason, reason_source, distance_miles } = recommendation;
  return (
    <section className="mt-8 rounded-2xl border border-blue bg-surface p-6">
      <p className="text-xs font-semibold tracking-wide text-blue uppercase">
        Recommended for you
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-ink">{event.title}</h2>
      <p className="mt-1 text-sm text-slate">
        {event.date} · {event.time} · {event.location}
        {distance_miles != null && ` · ${distance_miles} mi away`}
      </p>

      <div className="mt-4 rounded-xl bg-canvas p-4">
        <p className="text-sm font-medium text-ink">Why this event</p>
        <p className="mt-1 text-sm text-ink">{reason}</p>
        {reason_source === "fallback" && (
          <p className="mt-2 text-xs text-slate">
            Picked on topic, date and distance - our AI advisor is unavailable
            right now.
          </p>
        )}
      </div>

      <p className="mt-4 text-sm text-ink">{event.description}</p>
      <EventDetails event={event} />
    </section>
  );
}

// "View details" toggle that expands an event card in place, showing every
// field the list leaves out, with the event's chat at the bottom.
function EventDetails({ event }: { event: Event }) {
  const [open, setOpen] = useState(false);
  const detailsId = useId(); // unique even when the same event is shown twice

  const facts: [string, string][] = [
    ["Venue", event.venue],
    ["Duration", event.duration],
    ["Cost", event.cost],
    ["Format", event.format],
    ["Focus", event.focus],
    ["Audience", event.audience],
    ["Prerequisites", event.prerequisites],
    ["Registration", event.registration],
    ["Speakers", event.speakers],
  ];

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={detailsId}
        className="text-sm font-medium text-blue hover:underline"
      >
        {open ? "Hide details" : "View details"}
      </button>

      {open && (
        <div id={detailsId} className="mt-4 border-t border-line pt-4">
          <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
            {facts
              .filter(([, value]) => value)
              .map(([label, value]) => (
                <div key={label}>
                  <dt className="text-slate">{label}</dt>
                  <dd className="font-medium text-ink">{value}</dd>
                </div>
              ))}
          </dl>

          {event.agenda.length > 0 && (
            <DetailList title="Agenda" items={event.agenda} />
          )}
          {event.key_topics.length > 0 && (
            <DetailList title="Key topics" items={event.key_topics} />
          )}

          {/* Mounted only while open, so a card's chat loads on first view */}
          <EventChat eventId={event.id} />
        </div>
      )}
    </div>
  );
}

// Ask questions about one event. The backend answers plain facts (date,
// place, cost...) from the event data for free; anything else goes to the
// AI, up to max_chats questions per student per event.
function EventChat({ eventId }: { eventId: string }) {
  const chatUrl = `/api/intelligence/events/${eventId}/chat/`;
  const inputId = useId();
  const [chat, setChat] = useState<ChatState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<string | null>(null); // question being answered
  const [sendError, setSendError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ChatState>(chatUrl)
      .then(setChat)
      .catch((err) =>
        setLoadError(errorDetail(err, "Could not load the chat.")),
      );
  }, [chatUrl]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const asked = question.trim();
    if (!asked || pending) return; // blank, or still waiting on the last one

    setPending(asked);
    setSendError(null);
    try {
      // Every success returns the whole chat, so just replace it.
      setChat(await apiFetch<ChatState>(chatUrl, { question: asked }, true));
      setQuestion("");
    } catch (err) {
      // The question stays in the box so the student can try again.
      setSendError(
        errorDetail(err, "Could not send your question. Please try again."),
      );
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="mt-6 border-t border-line pt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">
          Ask about this event
        </h3>
        {chat && (
          <span className="text-xs text-slate">
            {chat.chats_remaining} of {chat.max_chats} questions left
          </span>
        )}
      </div>

      {loadError && <p className="mt-3 text-sm text-pink">{loadError}</p>}
      {!chat && !loadError && (
        <p className="mt-3 text-sm text-slate">Loading chat...</p>
      )}

      {chat && (
        <>
          {(chat.exchanges.length > 0 || pending) && (
            <ul className="mt-3 flex flex-col gap-3" aria-live="polite">
              {chat.exchanges.map((exchange, index) => (
                <li key={index} className="flex flex-col gap-1 text-sm">
                  <p className="self-end rounded-xl bg-blue px-3 py-2 text-white">
                    {exchange.question}
                  </p>
                  <p className="self-start rounded-xl bg-canvas px-3 py-2 text-ink">
                    {exchange.answer}
                  </p>
                  {exchange.source === "facts" && (
                    <span className="self-start text-xs text-slate">
                      From the event details - doesn&apos;t use a question
                    </span>
                  )}
                </li>
              ))}
              {pending && (
                <li className="flex flex-col gap-1 text-sm">
                  <p className="self-end rounded-xl bg-blue px-3 py-2 text-white">
                    {pending}
                  </p>
                  <p className="self-start px-3 py-2 text-slate">Thinking...</p>
                </li>
              )}
            </ul>
          )}

          {chat.chats_remaining === 0 && (
            <p className="mt-3 text-xs text-slate">
              You&apos;ve used all your questions for this event. You can still
              ask about the date, time, place or cost.
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
            <label htmlFor={inputId} className="sr-only">
              Your question
            </label>
            <input
              id={inputId}
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              maxLength={MAX_QUESTION_CHARS}
              disabled={pending !== null}
              placeholder="e.g. Is this good for a beginner?"
              className="min-w-0 flex-1 rounded-md border border-line bg-transparent px-3 py-2 text-sm text-ink outline-none focus:border-blue disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={pending !== null || !question.trim()}
              className="rounded-md bg-blue px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pending ? "Sending..." : "Ask"}
            </button>
          </form>

          {sendError && <p className="mt-2 text-sm text-pink">{sendError}</p>}
        </>
      )}
    </div>
  );
}

function DetailList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
