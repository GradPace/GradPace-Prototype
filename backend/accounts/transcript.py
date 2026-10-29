"""Reads an Old Dominion University unofficial transcript PDF into TakenClass
rows. Rule-based, like benchmarks/scoring.py: one known layout,
matched line by line. The PDF itself is never saved. Only the rows are.

pdfplumber turns the PDF into lines like these (made up):

    TRANSFER CREDIT ACCEPTED BY INSTITUTION
    HIST 101 WORLD HISTORY AP 3.000 0.00 I     <- skipped: no term to file it under
    INSTITUTION CREDIT
    Term: Fall 2025
    CS 999 UG DATA STRUCTURES & B+ 3.000 9.90  <- subject, number, level, title,
    ALGORITHMS                                    grade, credits, quality points;
    COURSE(S) IN PROGRESS                         the title wrapped onto its own line
    Term: Spring 2026
    CS 998 UG SOFTWARE ENGINEERING 3.000       <- no grade yet

Everything else (name, academic standing, GPA totals, column headers) is
ignored. A line that starts like a course but matches no row comes back in
`unparsed` rather than silently disappearing.
"""

import re
from dataclasses import dataclass, field

import pdfplumber

# Bounds the parsing work for one upload. A real transcript is a handful of pages.
MAX_PAGES = 20

# Section headings, each on a line of its own. The section decides which row
# layout applies (ROW_PATTERNS).
SECTIONS = {
    'TRANSFER CREDIT ACCEPTED BY INSTITUTION': 'transfer',
    'INSTITUTION CREDIT': 'institution',
    'COURSE(S) IN PROGRESS': 'in_progress',
    'TRANSCRIPT TOTALS': 'totals',
}

TERM_RE = re.compile(r'^Term: (Fall|Spring|Summer|Winter) (\d{4})$')

# Shared tail of a graded row: grade, credit hours, quality points and an
# optional repeat flag (I/E), which we don't use. The title before it is lazy,
# so the grade is always the last token before the credits.
_GRADED_TAIL = r'(?P<grade>[A-Z]{1,2}[+-]?) (?P<credits>\d+\.\d{3}) \d+\.\d{2}(?: [A-Z])?$'

ROW_PATTERNS = {
    # No Level column, and placeholder numbers like 1ELE (an elective).
    'transfer': re.compile(
        r'^(?P<subject>[A-Z]{2,4}) (?P<number>\d[0-9A-Z]{2,3}) (?P<title>.+?) ' + _GRADED_TAIL
    ),
    'institution': re.compile(
        r'^(?P<subject>[A-Z]{2,4}) (?P<number>\d{3}[A-Z]?) [A-Z]{2} (?P<title>.+?) ' + _GRADED_TAIL
    ),
    # No grade or quality points yet.
    'in_progress': re.compile(
        r'^(?P<subject>[A-Z]{2,4}) (?P<number>\d{3}[A-Z]?) [A-Z]{2} (?P<title>.+?) '
        r'(?P<credits>\d+\.\d{3})$'
    ),
}

LOOKS_LIKE_COURSE_RE = re.compile(r'^[A-Z]{2,4} \d[0-9A-Z]{2,3}\b')

TRANSFER_REASON = 'Transfer and AP credit has no term to file it under.'


class TranscriptError(Exception):
    """The upload isn't a readable ODU unofficial transcript. The message is
    safe to show the user."""


@dataclass
class ParseResult:
    # TakenClassSerializer input: course_code, course_name, semester, year,
    # grade, credits.
    courses: list[dict] = field(default_factory=list)
    # Rows that won't be imported: course_code, course_name, semester, year,
    # reason.
    skipped: list[dict] = field(default_factory=list)
    # Course-like lines that matched no row layout, as-is.
    unparsed: list[str] = field(default_factory=list)


def extract_lines(file):
    """PDF file object -> its non-blank text lines, every page joined (a
    wrapped title can continue onto the next page), whitespace collapsed."""
    try:
        with pdfplumber.open(file) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise TranscriptError(f'Transcripts can be at most {MAX_PAGES} pages.')
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except TranscriptError:
        raise
    except Exception as exc:
        # Untrusted input - pdfminer can fail in many ways (corrupt file,
        # password-protected, ...), and they all mean the same thing here.
        raise TranscriptError("Couldn't read this PDF.") from exc
    return [' '.join(line.split()) for line in text.splitlines() if line.strip()]


def parse_lines(lines):
    """Transcript text lines -> ParseResult. Raises TranscriptError if none
    of ODU's section headings appear."""
    result = ParseResult()
    section = None
    semester = year = None
    # The row a wrapped title line belongs to - only ever the row just before.
    last_row = None

    for line in lines:
        if line in SECTIONS:
            section = SECTIONS[line]
            semester = year = None
            last_row = None
            continue

        if term := TERM_RE.match(line):
            semester, year = term[1].lower(), int(term[2])
            last_row = None
            continue

        pattern = ROW_PATTERNS.get(section)
        match = pattern.match(line) if pattern else None
        if match and (section == 'transfer' or semester):
            last_row = _add_row(result, match, section, semester, year)
            continue

        if pattern and LOOKS_LIKE_COURSE_RE.match(line):
            result.unparsed.append(line)
            last_row = None
            continue

        # Wrapped title text is uppercase like the rest of the row. Every
        # other line in the layout (standing, totals, column headers) has
        # lowercase in it.
        if last_row is not None and not any(char.islower() for char in line):
            # A title broken after a slash or hyphen ('DESIGN/' + 'TESTING')
            # was one word on the transcript - no space between the halves.
            separator = '' if last_row['course_name'].endswith(('/', '-')) else ' '
            last_row['course_name'] += separator + line
            continue

        last_row = None

    if section is None:
        raise TranscriptError("This doesn't look like an ODU unofficial transcript.")
    return result


def parse_transcript(file):
    return parse_lines(extract_lines(file))


def _add_row(result, match, section, semester, year):
    row = {
        'course_code': f'{match["subject"]} {match["number"]}',
        'course_name': match['title'],
        'semester': semester,
        'year': year,
    }
    if section == 'transfer':
        row['reason'] = TRANSFER_REASON
        result.skipped.append(row)
    else:
        # 'grade' isn't in the in-progress pattern. TakenClass.credits is
        # whole hours - ODU prints them as e.g. 3.000.
        row['grade'] = match.groupdict().get('grade') or ''
        row['credits'] = int(float(match['credits']))
        result.courses.append(row)
    return row
