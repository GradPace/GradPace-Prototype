import { useEffect, useId, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import { ApiError, apiGet } from "../../lib/api/api";

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

// The backend's 404 body when the student hasn't set up a profile yet
const NO_PROFILE_DETAIL = "No student profile yet.";

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
// field the list leaves out. The chat box will go at the bottom of this later.
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
        </div>
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
