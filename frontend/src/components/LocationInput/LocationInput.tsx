import { useEffect, useId, useState } from "react";
import { searchPlaces, type Place } from "../../lib/api/places";

const MIN_QUERY_LENGTH = 2;

interface Props {
  name: string;
  className?: string;
  // Starting text, e.g. a saved location when editing a profile.
  defaultValue?: string;
  // How long to wait after the last keystroke before asking the backend.
  debounceMs?: number;
}

// A text box that suggests US places as you type ("nor" -> "Norfolk, VA").
// Uses the browser's native <datalist>, so it's still a plain input: anything
// can be typed, and the value is whatever is in the box (read it through the
// form's `name`). Picking a suggestion makes the saved location an exact
// "City, ST", which the backend can find for event distances.
export default function LocationInput({ name, className, defaultValue = "", debounceMs = 200 }: Props) {
  const listId = useId();
  const [text, setText] = useState(defaultValue);
  // Results are stored with the query they answer, so a slow reply for
  // "nor" can never show up under what's now "norfolk".
  const [result, setResult] = useState<{ query: string; places: Place[] }>({
    query: "",
    places: [],
  });

  const query = text.trim();

  useEffect(() => {
    if (query.length < MIN_QUERY_LENGTH) return;

    let stale = false;
    const timer = setTimeout(() => {
      searchPlaces(query)
        .then((places) => {
          if (!stale) setResult({ query, places });
        })
        // Suggestions are a nicety - if the lookup fails the box still works.
        .catch(() => {});
    }, debounceMs);

    return () => {
      stale = true;
      clearTimeout(timer);
    };
  }, [query, debounceMs]);

  const options = result.query === query ? result.places : [];

  return (
    <>
      <input
        type="text"
        name={name}
        value={text}
        onChange={(event) => setText(event.target.value)}
        list={listId}
        // Browser autofill would fight with the suggestions.
        autoComplete="off"
        className={className}
      />
      <datalist id={listId}>
        {options.map((place) => (
          <option key={place.label} value={place.label} />
        ))}
      </datalist>
    </>
  );
}
