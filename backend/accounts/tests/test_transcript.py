from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from rest_framework.throttling import ScopedRateThrottle

from ..factories import StudentProfileFactory, TakenClassFactory, UserFactory
from ..models import TakenClass
from ..transcript import TRANSFER_REASON, ParseResult, TranscriptError, parse_lines
from .helpers import login

URL = '/api/auth/profile/transcript/'

# Made-up ODU unofficial transcript, as pdfplumber extracts one. PAGE_BREAK
# lines start a new page in the PDF and are dropped from the text.
SAMPLE = (Path(__file__).parent / 'fixtures' / 'transcript_sample.txt').read_text()
PAGE_BREAK = '--- page break ---'

# Everything SAMPLE's graded and in-progress sections list, in order.
SAMPLE_COURSES = [
    ('CS 150', 'PROBLEM SOLVING AND PROGRAMMING I', 'fall', 2024, 'B+', 4),
    ('MATH 163', 'PRECALCULUS II', 'fall', 2024, 'C', 3),
    ('CS 120G', 'INFORMATION LITERACY', 'fall', 2024, 'P', 1),
    ('MATH 163', 'PRECALCULUS II', 'spring', 2025, 'A-', 3),
    ('CHEM 121N', 'FOUNDATIONS OF CHEMISTRY I LAB', 'spring', 2025, 'A', 1),
    ('PHYS 111N', 'INTRO PHYSICS', 'spring', 2025, 'A', 4),
    ('CS 300T', 'COMPUTERS IN SOCIETY', 'fall', 2025, 'A', 3),
    ('CS 300T', 'COMPUTERS IN SOCIETY', 'fall', 2025, '', 3),
    ('CS 432', 'WEB SCIENCE', 'fall', 2025, '', 3),
    ('CS 418', 'WEB PROGRAMMING AND DESIGN', 'spring', 2026, '', 3),
]
# What gets imported - the in-progress CS 300T repeats the graded one.
IMPORTED = SAMPLE_COURSES[:7] + SAMPLE_COURSES[8:]


def sample_lines():
    return [line for line in SAMPLE.splitlines() if line and line != PAGE_BREAK]


def as_tuples(courses):
    keys = ('course_code', 'course_name', 'semester', 'year', 'grade', 'credits')
    return [tuple(course[key] for key in keys) for course in courses]


def make_pdf(text):
    pdf = FPDF()
    pdf.set_font('helvetica', size=9)
    pdf.add_page()
    for line in text.splitlines():
        if line == PAGE_BREAK:
            pdf.add_page()
        else:
            pdf.cell(text=line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


def pdf_upload(text=SAMPLE, name='transcript.pdf'):
    return SimpleUploadedFile(name, make_pdf(text), content_type='application/pdf')


def upload(client, tokens, file=None, **data):
    return client.post(
        URL,
        {'file': file or pdf_upload(), **data},
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )


# parse_lines


def test_parses_graded_and_in_progress_courses():
    result = parse_lines(sample_lines())

    assert as_tuples(result.courses) == SAMPLE_COURSES
    assert result.unparsed == []


def test_skips_transfer_credit():
    result = parse_lines(sample_lines())

    assert result.skipped == [
        {
            'course_code': 'HIST 101H',
            'course_name': 'WORLD CIVILIZATIONS',
            'semester': None,
            'year': None,
            'reason': TRANSFER_REASON,
        },
        {
            'course_code': 'CS 1ELE',
            'course_name': 'ELECTIVE',
            'semester': None,
            'year': None,
            'reason': TRANSFER_REASON,
        },
    ]


def test_reports_course_like_lines_it_cannot_read():
    result = parse_lines(
        [
            'INSTITUTION CREDIT',
            'Term: Fall 2025',
            'CS 999 UG A ROW WITH NO CREDITS',
            'CS 998 UG A NORMAL ROW A 3.000 12.00',
        ]
    )

    assert result.unparsed == ['CS 999 UG A ROW WITH NO CREDITS']
    assert as_tuples(result.courses) == [
        ('CS 998', 'A NORMAL ROW', 'fall', 2025, 'A', 3),
    ]


def test_a_row_before_any_term_is_unparsed():
    result = parse_lines(['INSTITUTION CREDIT', 'CS 998 UG A NORMAL ROW A 3.000 12.00'])

    assert result.courses == []
    assert result.unparsed == ['CS 998 UG A NORMAL ROW A 3.000 12.00']


def test_a_title_wrapped_after_a_slash_or_hyphen_joins_without_a_space():
    result = parse_lines(
        [
            'INSTITUTION CREDIT',
            'Term: Fall 2025',
            'CS 997 UG SOFTWARE DESIGN/ A 3.000 12.00',
            'TESTING',
            'CS 996 UG SENIOR PROJECT I- A 3.000 12.00',
            'CAPSTONE',
        ]
    )

    assert [course['course_name'] for course in result.courses] == [
        'SOFTWARE DESIGN/TESTING',
        'SENIOR PROJECT I-CAPSTONE',
    ]


def test_a_line_with_lowercase_ends_a_wrapped_title():
    result = parse_lines(
        [
            'INSTITUTION CREDIT',
            'Term: Fall 2025',
            'CS 998 UG A NORMAL ROW A 3.000 12.00',
            'Term Totals Attempt Hours Passed Hours',
            'HS: NOT PART OF THE TITLE',
        ]
    )

    assert result.courses[0]['course_name'] == 'A NORMAL ROW'


def test_rejects_text_that_is_not_an_odu_transcript():
    with pytest.raises(TranscriptError):
        parse_lines(['Some other document', 'CS 998 UG A NORMAL ROW A 3.000 12.00'])


# The upload endpoint


@pytest.mark.django_db
def test_requires_authentication(client):
    response = client.post(URL, {'file': pdf_upload()})

    assert response.status_code == 401


@pytest.mark.django_db
def test_requires_a_profile(client):
    tokens = login(client, UserFactory())

    response = upload(client, tokens)

    assert response.status_code == 404


@pytest.mark.django_db
def test_rejects_a_json_body(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = client.post(
        URL,
        {'file': 'not a file'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 415


@pytest.mark.django_db
@pytest.mark.parametrize(
    'file',
    [
        SimpleUploadedFile('transcript.pdf', b'just some text', content_type='application/pdf'),
        SimpleUploadedFile('transcript.txt', make_pdf(SAMPLE), content_type='text/plain'),
    ],
    ids=['not-a-pdf', 'wrong-extension'],
)
def test_rejects_files_that_are_not_pdfs(client, file):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = upload(client, tokens, file=file)

    assert response.status_code == 400
    assert response.json() == {'file': ['Upload your transcript as a PDF.']}


@pytest.mark.django_db
def test_rejects_a_file_over_the_size_limit(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    with patch('accounts.serializers.transcript.MAX_TRANSCRIPT_BYTES', 100):
        response = upload(client, tokens)

    assert response.status_code == 400
    assert response.json() == {'file': ['Transcript must be 5 MB or smaller.']}


@pytest.mark.django_db
def test_rejects_a_corrupt_pdf(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)
    file = SimpleUploadedFile('transcript.pdf', b'%PDF-1.7 truncated garbage')

    response = upload(client, tokens, file=file)

    assert response.status_code == 400
    assert response.json() == {'file': ["Couldn't read this PDF."]}


@pytest.mark.django_db
def test_rejects_a_pdf_that_is_not_a_transcript(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = upload(client, tokens, file=pdf_upload('Just a letter.'))

    assert response.status_code == 400
    assert response.json() == {'file': ["This doesn't look like an ODU unofficial transcript."]}


@pytest.mark.django_db
def test_rejects_a_pdf_with_too_many_pages(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    with patch('accounts.transcript.MAX_PAGES', 1):
        response = upload(client, tokens)

    assert response.status_code == 400
    assert response.json() == {'file': ['Transcripts can be at most 1 pages.']}


@pytest.mark.django_db
def test_dry_run_reports_without_saving(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = upload(client, tokens, dry_run='true')

    assert response.status_code == 200
    body = response.json()
    assert as_tuples(body['courses']) == IMPORTED
    assert [course['course_code'] for course in body['skipped']] == [
        'HIST 101H',
        'CS 1ELE',
        'CS 300T',
    ]
    assert body['skipped'][2]['reason'] == 'Listed twice for the same term.'
    assert body['unparsed'] == []
    assert not TakenClass.objects.exists()


@pytest.mark.django_db
def test_upload_saves_the_classes_to_the_callers_profile(client):
    """Through a real multi-page PDF, so a title wrapped across a page break
    is covered too (CHEM 121N)."""
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = upload(client, tokens)

    assert response.status_code == 201
    body = response.json()
    assert as_tuples(body['courses']) == IMPORTED
    assert all(course['id'] for course in body['courses'])

    saved = TakenClass.objects.filter(student=profile)
    assert saved.count() == len(IMPORTED)
    assert saved.get(course_code='CS 150').grade == 'B+'


@pytest.mark.django_db
def test_uploading_again_skips_classes_already_on_the_profile(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)
    upload(client, tokens)

    response = upload(client, tokens)

    assert response.status_code == 201
    body = response.json()
    assert body['courses'] == []
    reasons = [course['reason'] for course in body['skipped']]
    # Including the in-progress CS 300T - the graded one is on the profile now.
    assert reasons.count('Already on your profile.') == len(SAMPLE_COURSES)
    assert TakenClass.objects.filter(student=profile).count() == len(IMPORTED)


@pytest.mark.django_db
def test_other_students_classes_do_not_count_as_already_on_the_profile(client):
    other = TakenClassFactory(course_code='CS 150', semester='fall', year=2024)
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = upload(client, tokens)

    assert len(response.json()['courses']) == len(IMPORTED)
    assert TakenClass.objects.filter(student=other.student).count() == 1


@pytest.mark.django_db
def test_rows_that_fail_validation_are_skipped_not_saved(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)
    parsed = ParseResult(
        courses=[
            {
                'course_code': 'CS 998',
                'course_name': 'A NORMAL ROW',
                'semester': 'fall',
                'year': 1800,
                'grade': 'A',
                'credits': 3,
            }
        ]
    )

    with patch('accounts.views.parse_transcript', return_value=parsed):
        response = upload(client, tokens)

    assert response.status_code == 201
    body = response.json()
    assert body['courses'] == []
    assert body['skipped'][0]['course_code'] == 'CS 998'
    assert '1900' in body['skipped'][0]['reason']
    assert not TakenClass.objects.exists()


@pytest.mark.django_db
def test_upload_is_throttled_per_user(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {'transcript': '1/hour'}):
        assert upload(client, tokens, dry_run='true').status_code == 200
        assert upload(client, tokens, dry_run='true').status_code == 429
