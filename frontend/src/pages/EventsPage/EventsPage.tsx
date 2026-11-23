import { useEffect, useState } from "react";
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

        <div className="mt-8">
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
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
