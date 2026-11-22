"""Event ranking (intelligence/events.py) - no database, no model."""

from datetime import date

import pytest

from .. import events

TODAY = date(2026, 11, 20)


def test_only_hampton_roads_events_are_loaded():
    cities = {event['city'] for event in events.load_events()}

    assert 'norfolk' in cities
    assert 'yorktown' in cities
    # Richmond/Petersburg/Emporia are in Virginia but not Hampton Roads; the
    # rest are North Carolina.
    assert cities.isdisjoint({'richmond', 'petersburg', 'emporia', 'hopewell', 'edenton'})
    assert len(events.load_events()) == 12


def test_event_ids_are_unique_slugs():
    ids = [event['id'] for event in events.load_events()]

    assert len(ids) == len(set(ids))
    assert 'datacore-database-engineering-conference' in ids


def test_get_event_finds_by_id_and_misses_unknown_or_out_of_region():
    assert events.get_event('datacore-database-engineering-conference')['city'] == 'yorktown'
    assert events.get_event('nope') is None
    assert events.get_event('datavision-analytics-and-visualization-summit') is None  # Richmond


def test_upcoming_events_drops_past_ones_but_keeps_today():
    titles = [e['title'] for e in events.upcoming_events(date(2026, 11, 24))]

    assert titles[0].startswith('CyberDefend')  # the 24th itself
    assert not any(t.startswith('AI Horizons') for t in titles)  # the 20th


def test_every_event_resolves_to_a_place_with_coordinates():
    for event in events.load_events():
        assert event['place'].label.casefold() == event['location'].casefold() or (
            event['city'] == 'gloucester'  # filed by the Census as "Gloucester Courthouse"
        )
        assert event['place'].lat and event['place'].lon


def test_distance_is_zero_for_the_same_city_and_grows_with_the_gap():
    datacore = events.get_event('datacore-database-engineering-conference')  # Yorktown

    assert events.distance_miles(datacore, 'Yorktown, VA') == 0
    assert 20 < events.distance_miles(datacore, 'Norfolk, VA') < 40
    assert events.distance_miles(datacore, 'Boston, MA') > 400


def test_distance_is_none_when_the_location_is_unknown_or_ambiguous():
    datacore = events.get_event('datacore-database-engineering-conference')

    assert events.distance_miles(datacore, '') is None
    assert events.distance_miles(datacore, 'Nowhereville, ZZ') is None
    assert events.distance_miles(datacore, 'Norfolk') is None  # no state: several Norfolks


def test_a_student_far_outside_the_region_still_gets_ranked_just_by_the_rest():
    ranked = events.rank_events([], 'Boston, MA', TODAY)

    assert ranked
    assert all(e['distance_miles'] > 400 for e in ranked)


def test_skill_fit_is_the_share_of_gap_weight_the_event_covers():
    datacore = events.get_event('datacore-database-engineering-conference')
    gaps = [{'label': 'SQL', 'weight': 0.3}, {'label': 'Kubernetes', 'weight': 0.1}]

    assert events.skill_fit(datacore, gaps) == pytest.approx(
        0.75
    )  # SQL matches, Kubernetes doesn't


def test_skill_fit_matches_plurals_and_is_zero_without_gaps():
    datacore = events.get_event('datacore-database-engineering-conference')

    assert events.skill_fit(datacore, [{'label': 'Databases', 'weight': 1}]) == 1.0
    assert events.skill_fit(datacore, []) == 0.0


def test_rank_puts_the_event_matching_a_gap_first_even_over_nearer_ones():
    gaps = [{'label': 'SQL', 'weight': 0.35}]

    ranked = events.rank_events(gaps, 'Norfolk, VA', TODAY)

    assert ranked[0]['id'] == 'datacore-database-engineering-conference'
    assert ranked[0]['skill_fit'] == 1.0
    assert [e['score'] for e in ranked] == sorted((e['score'] for e in ranked), reverse=True)


def test_rank_reports_distance_from_the_students_city():
    by_id = {e['id']: e for e in events.rank_events([], 'Norfolk, VA', TODAY)}

    assert by_id['cloudlaunch-modern-infrastructure-workshop']['distance_miles'] < 20  # Chesapeake
    assert by_id['human-first-ux-research-and-design-studio']['distance_miles'] > 30  # Gloucester


def test_rank_scores_the_same_event_higher_for_a_closer_student():
    def score(location):
        ranked = events.rank_events([], location, TODAY)
        return next(e for e in ranked if e['city'] == 'gloucester')['score']

    assert score('Gloucester, VA') > score('Norfolk, VA') > score('Suffolk, VA')


def test_rank_without_gaps_or_a_known_location_falls_back_to_soonest():
    ranked = events.rank_events([], '', TODAY)

    assert ranked[0]['date'] == '2026-11-20'
    assert ranked[0]['distance_miles'] is None  # unknown location


def test_rank_excludes_past_events():
    ranked = events.rank_events([], 'Norfolk, VA', date(2026, 12, 10))

    assert all(e['date'] >= '2026-12-10' for e in ranked)
    assert ranked  # but some are left


def test_rank_is_empty_once_every_event_has_passed():
    assert events.rank_events([], 'Norfolk, VA', date(2030, 1, 1)) == []
