"""US places (data/places.csv, built from the Census Gazetteer by
data/build_places.py): look up a "City, ST" and get coordinates for the
event-distance calculation, and search by prefix for the location
autocomplete. All in memory, no external service - a student's location
never leaves the backend.
"""

import csv
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PLACES_PATH = Path(__file__).parent / 'data' / 'places.csv'

STATE_NAMES = {
    'AL': 'Alabama',
    'AK': 'Alaska',
    'AZ': 'Arizona',
    'AR': 'Arkansas',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DE': 'Delaware',
    'DC': 'District of Columbia',
    'FL': 'Florida',
    'GA': 'Georgia',
    'HI': 'Hawaii',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'IA': 'Iowa',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'ME': 'Maine',
    'MD': 'Maryland',
    'MA': 'Massachusetts',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MS': 'Mississippi',
    'MO': 'Missouri',
    'MT': 'Montana',
    'NE': 'Nebraska',
    'NV': 'Nevada',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NY': 'New York',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VT': 'Vermont',
    'VA': 'Virginia',
    'WA': 'Washington',
    'WV': 'West Virginia',
    'WI': 'Wisconsin',
    'WY': 'Wyoming',
    'PR': 'Puerto Rico',
}
_STATE_BY_NAME = {name.casefold(): abbr for abbr, name in STATE_NAMES.items()}

# Names people use that the Census files under another name. Keyed by
# (casefolded name, state).
ALIASES = {
    # The county seat is a CDP called "Gloucester Courthouse".
    ('gloucester', 'VA'): 'Gloucester Courthouse',
}

# "Norfolk, VA", "Norfolk, Virginia" or "Norfolk, VA 23510".
_CITY_STATE = re.compile(
    r'^\s*(?P<name>[^,]+?)\s*,\s*(?P<state>[A-Za-z][A-Za-z .]*?)\s*(?:\d{5}(?:-\d{4})?)?\s*$'
)


@dataclass(frozen=True)
class Place:
    name: str
    state: str
    lat: float
    lon: float
    population: int
    area_sqmi: float

    @property
    def label(self):
        return f'{self.name}, {self.state}'


def _size(place):
    """Bigger places sort first: population, then land area (CDPs have no
    population estimate)."""
    return (place.population, place.area_sqmi)


@lru_cache(maxsize=1)
def _places():
    with PLACES_PATH.open(encoding='utf-8', newline='') as places_file:
        return tuple(
            Place(
                r['name'],
                r['state'],
                float(r['lat']),
                float(r['lon']),
                int(r['population']),
                float(r['area_sqmi']),
            )
            for r in csv.DictReader(places_file)
        )


@lru_cache(maxsize=1)
def _by_name_and_state():
    """(casefolded name, state) -> the place; the biggest if several share it."""
    best = {}
    for place in _places():
        key = (place.name.casefold(), place.state)
        if key not in best or _size(place) > _size(best[key]):
            best[key] = place
    return best


@lru_cache(maxsize=1)
def _by_name():
    by_name = {}
    for place in _places():
        by_name.setdefault(place.name.casefold(), []).append(place)
    return by_name


def _state_code(text):
    text = text.strip().strip('.').casefold()
    if len(text) == 2 and text.upper() in STATE_NAMES:
        return text.upper()
    return _STATE_BY_NAME.get(text)


def lookup(text):
    """The Place a free-text location names, or None. Wants a state
    ("Norfolk, VA" / "Norfolk, Virginia" / with a ZIP); a bare city name only
    resolves if exactly one place in the US has it."""
    text = (text or '').strip()
    if not text:
        return None

    match = _CITY_STATE.match(text)
    if match:
        state = _state_code(match['state'])
        if state is None:
            return None
        name = match['name'].casefold()
        name = ALIASES.get((name, state), name).casefold()
        return _by_name_and_state().get((name, state))

    candidates = _by_name().get(text.casefold(), [])
    return candidates[0] if len(candidates) == 1 else None


def search(query, limit=8):
    """Autocomplete: places whose name starts with the query, best first.
    "nor" and "norfolk, v" both work; the part after a comma narrows by state
    (abbreviation or full name). Exact name matches come first, then bigger
    places (by population) before smaller ones."""
    text = ' '.join((query or '').casefold().split())
    name_part, _, state_part = text.partition(',')
    name_part, state_part = name_part.strip(), state_part.strip()
    if len(name_part) < 2:
        return []

    matches = []
    for place in _places():
        folded = place.name.casefold()
        if not folded.startswith(name_part):
            continue
        if state_part and not (
            place.state.casefold().startswith(state_part)
            or STATE_NAMES[place.state].casefold().startswith(state_part)
        ):
            continue
        matches.append(place)

    matches.sort(
        key=lambda p: (p.name.casefold() != name_part, -p.population, -p.area_sqmi, p.label)
    )
    return matches[:limit]


def miles_between(a, b):
    """Great-circle distance between two Places, in miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 3958.8 * 2 * math.asin(math.sqrt(h))
