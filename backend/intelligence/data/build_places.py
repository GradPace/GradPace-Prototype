"""Build places.csv from the US Census Gazetteer of places.

places.csv is every incorporated place and census-designated place in the US
(~32,000), with a point near its center. It feeds the location autocomplete
and the event-distance calculation (intelligence/places.py).

Sources (public domain, kept outside the repo):
    https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_place_national.zip
    https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/cities/totals/sub-est2023.csv

The second gives each incorporated place's 2023 population estimate, used to
rank autocomplete results. CDPs have no estimate and get 0.

Run from backend/ with the unzipped Gazetteer .txt and the population CSV:

    uv run intelligence/data/build_places.py \\
        --gazetteer <dir>/2023_Gaz_place_national.txt --population <dir>/sub-est2023.csv
"""

import argparse
import csv
import re
from pathlib import Path

OUT_PATH = Path(__file__).parent / 'places.csv'

# The Gazetteer's names end with the kind of place ("Norfolk city", "Yorktown
# CDP"). Students don't type that, so it's dropped. Longest first so
# "city and borough" isn't cut down to "city".
SUFFIXES = [
    'consolidated government',
    'metropolitan government',
    'unified government',
    'metro government',
    'city and borough',
    'urban county',
    'municipality',
    'comunidad',
    'zona urbana',
    'township',
    'borough',
    'village',
    'town',
    'city',
    'CDP',
]
# "(balance)" marks a place with a smaller one carved out of it - "Milford city
# (balance)" - and goes too.
SUFFIX_RE = re.compile(
    r'\s+(?:' + '|'.join(re.escape(s) for s in SUFFIXES) + r')(?:\s+\(balance\))?$'
)


def read_populations(population_path):
    """{state FIPS + place FIPS: 2023 population estimate}, for incorporated
    places (SUMLEV 162) and consolidated cities (170)."""
    populations = {}
    with open(population_path, encoding='latin-1', newline='') as source:
        for record in csv.DictReader(source):
            if record['SUMLEV'] in ('162', '170'):
                populations[record['STATE'] + record['PLACE']] = int(record['POPESTIMATE2023'])
    return populations


def build(gazetteer_path, population_path):
    populations = read_populations(population_path)
    rows = []
    with open(gazetteer_path, encoding='utf-8', newline='') as source:
        reader = csv.DictReader(source, delimiter='\t')
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        for record in reader:
            name = SUFFIX_RE.sub('', record['NAME'].strip())
            rows.append(
                (
                    name,
                    record['USPS'].strip(),
                    f'{float(record["INTPTLAT"]):.4f}',
                    f'{float(record["INTPTLONG"]):.4f}',
                    populations.get(record['GEOID'].strip(), 0),
                    f'{float(record["ALAND_SQMI"]):.1f}',
                )
            )
    rows.sort(key=lambda row: (row[1], row[0].casefold(), row[0]))
    with OUT_PATH.open('w', encoding='utf-8', newline='') as out:
        writer = csv.writer(out, lineterminator='\n')
        writer.writerow(['name', 'state', 'lat', 'lon', 'population', 'area_sqmi'])
        writer.writerows(rows)
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--gazetteer', required=True, type=Path)
    parser.add_argument('--population', required=True, type=Path)
    args = parser.parse_args()
    print(f'wrote {build(args.gazetteer, args.population)} places to {OUT_PATH}')
