"""US places lookup and search (intelligence/places.py) - no database."""

import pytest

from .. import places


def test_the_table_covers_the_whole_country():
    states = {place.state for place in places._places()}

    assert len(places._places()) > 30000
    assert {'VA', 'NC', 'CA', 'TX', 'NY', 'AK', 'HI', 'DC'} <= states


@pytest.mark.parametrize(
    'text',
    [
        'Norfolk, VA',
        'norfolk, va',
        'Norfolk, Virginia',
        'Norfolk,VA',
        'Norfolk, VA 23510',
        '  Norfolk , VA  ',
    ],
)
def test_lookup_reads_city_and_state_in_the_usual_forms(text):
    place = places.lookup(text)

    assert (place.name, place.state) == ('Norfolk', 'VA')
    assert 36 < place.lat < 37.5
    assert -77 < place.lon < -76


def test_lookup_keeps_the_state_straight():
    assert places.lookup('Norfolk, NE').state == 'NE'
    assert places.lookup('Springfield, IL').state == 'IL'


def test_lookup_resolves_a_bare_name_only_when_it_is_unique():
    assert places.lookup('Norfolk') is None  # Norfolk VA, NE, CT, ...
    assert places.lookup('Virginia Beach').state == 'VA'  # only one


def test_lookup_uses_aliases_for_names_the_census_files_differently():
    assert places.lookup('Gloucester, VA').name == 'Gloucester Courthouse'


@pytest.mark.parametrize('text', ['', None, '   ', 'Atlantis, ZZ', 'Nowhereville, VA', ',', 'VA'])
def test_lookup_is_none_for_blank_or_unknown_places(text):
    assert places.lookup(text) is None


def test_search_matches_by_prefix_and_ranks_bigger_places_first():
    labels = [p.label for p in places.search('new y')]

    assert labels[0] == 'New York, NY'
    assert all(label.casefold().startswith('new y') for label in labels)


def test_search_can_be_narrowed_by_state_abbreviation_or_name():
    assert [p.label for p in places.search('norfolk, v')] == ['Norfolk, VA']
    assert [p.label for p in places.search('franklin, virginia')][0] == 'Franklin, VA'
    assert {p.state for p in places.search('spring, t')} <= {'TX', 'TN'}


def test_search_puts_an_exact_name_before_longer_ones():
    labels = [p.label for p in places.search('franklin')]

    assert labels[0].startswith('Franklin,')
    assert not labels[0].startswith('Franklin Park')


def test_search_needs_at_least_two_letters_and_respects_the_limit():
    assert places.search('n') == []
    assert places.search('') == []
    assert places.search(None) == []
    assert len(places.search('sa', limit=3)) == 3


def test_search_finds_nothing_for_gibberish():
    assert places.search('zzzzqq') == []


def test_miles_between_is_zero_for_the_same_place_and_sensible_for_others():
    norfolk = places.lookup('Norfolk, VA')

    assert places.miles_between(norfolk, norfolk) == 0
    assert 20 < places.miles_between(norfolk, places.lookup('Yorktown, VA')) < 35
    assert 2300 < places.miles_between(norfolk, places.lookup('Los Angeles, CA')) < 2400
