import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import SurveyResultsTab from './SurveyResultsTab'
import { getSurveyResults, type SurveyResults } from '../../lib/api/admin'
import { ApiError } from '../../lib/api/api'

vi.mock('../../lib/api/admin', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/api/admin')>()),
  getSurveyResults: vi.fn(),
}))

function distribution(...counts: number[]) {
  return counts.map((count, index) => ({ value: index + 1, count }))
}

function feedback(count: number) {
  return Array.from({ length: count }, (_, n) => ({
    text: `Feedback ${n}`,
    submitted_at: new Date(Date.UTC(2026, 10, 30 - n)).toISOString(),
  }))
}

function results(overrides: Partial<SurveyResults> = {}): SurveyResults {
  return {
    response_count: 10,
    latest_submitted_at: '2026-11-20T14:03:11Z',
    ratings: {
      preparedness_rating: { average: 3.75, distribution: distribution(1, 0, 2, 5, 2) },
      platform_helpfulness_rating: { average: 4.08, distribution: distribution(0, 1, 1, 3, 5) },
    },
    by_industry: [
      { code: 'software', label: 'Software / Tech', count: 4, preparedness_average: 3.5, platform_helpfulness_average: 4.25 },
      { code: 'it_services', label: 'IT services', count: 0, preparedness_average: null, platform_helpfulness_average: null },
      { code: 'finance', label: 'Finance / Banking', count: 2, preparedness_average: null, platform_helpfulness_average: null },
      { code: 'healthcare', label: 'Healthcare', count: 4, preparedness_average: 4, platform_helpfulness_average: 3.75 },
    ],
    top_skills: [
      { name: 'Amazon Web Services AWS software', label: 'AWS', count: 6 },
      { name: 'Python', label: 'Python', count: 3 },
    ],
    suggested_skills: [
      { skill: 'Rust', count: 4 },
      { skill: 'LLM tooling', count: 2 },
    ],
    feedback_count: 3,
    feedback: feedback(3),
    ...overrides,
  }
}

async function renderTab(data: SurveyResults = results()) {
  vi.mocked(getSurveyResults).mockResolvedValue(data)
  render(<SurveyResultsTab />)
  await screen.findByText('Ratings')
}

function tile(label: string) {
  return within(screen.getByText(label, { selector: 'p' }).parentElement as HTMLElement)
}

function rowFor(text: string) {
  return within(screen.getByText(text).closest('tr') as HTMLElement)
}

function industryNames() {
  const table = screen.getByText('Industry').closest('table') as HTMLElement
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map((row) => (row as HTMLTableRowElement).cells[0].textContent)
}

describe('SurveyResultsTab', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the summary tiles', async () => {
    await renderTab()

    expect(tile('Responses').getByText('10')).toBeInTheDocument()
    expect(tile('Average preparedness').getByText('3.8')).toBeInTheDocument()
    expect(tile('Average GradPace helpfulness').getByText('4.1')).toBeInTheDocument()
    expect(
      tile('Latest response').getByText(new Date('2026-11-20T14:03:11Z').toLocaleDateString()),
    ).toBeInTheDocument()
  })

  it('shows No data when an average is missing', async () => {
    await renderTab(
      results({
        latest_submitted_at: null,
        ratings: {
          preparedness_rating: { average: null, distribution: distribution(0, 0, 0, 0, 0) },
          platform_helpfulness_rating: { average: null, distribution: distribution(0, 0, 0, 0, 0) },
        },
      }),
    )

    expect(tile('Average preparedness').getByText('No data')).toBeInTheDocument()
    expect(tile('Average GradPace helpfulness').getByText('No data')).toBeInTheDocument()
    expect(tile('Latest response').getByText('No data')).toBeInTheDocument()
  })

  it('draws a bar per rating value with its count', async () => {
    await renderTab()

    expect(screen.getByText('How prepared alumni felt for their first job')).toBeInTheDocument()
    expect(screen.getByText('How much GradPace helped them get there')).toBeInTheDocument()
    const counts = [1, 0, 2, 5, 2]
    counts.forEach((count, index) => {
      const row = screen.getByTestId(`preparedness_rating-${index + 1}`)
      // Value, bar, count - the count is the last cell.
      expect(row.lastElementChild?.textContent).toBe(String(count))
      const fill = row.querySelector('[aria-hidden] > div') as HTMLElement
      expect(fill.style.width).toBe(`${(count / 10) * 100}%`)
    })
    expect(screen.getByTestId('platform_helpfulness_rating-5').lastElementChild?.textContent).toBe(
      '5',
    )
  })

  it('lists industries with responses, most first, and hides small averages', async () => {
    await renderTab()

    expect(industryNames()).toEqual(['Software / Tech', 'Healthcare', 'Finance / Banking'])
    expect(screen.queryByText('IT services')).not.toBeInTheDocument()
    const software = rowFor('Software / Tech')
    expect(software.getByText('3.5')).toBeInTheDocument()
    expect(software.getByText('4.3')).toBeInTheDocument()
    expect(rowFor('Finance / Banking').getAllByText('Too few responses')).toHaveLength(2)
  })

  it('shows top and suggested skills with counts', async () => {
    await renderTab()

    expect(rowFor('AWS').getByText('6')).toBeInTheDocument()
    expect(rowFor('Python').getByText('3')).toBeInTheDocument()
    expect(rowFor('Rust').getByText('4')).toBeInTheDocument()
    expect(rowFor('LLM tooling').getByText('2')).toBeInTheDocument()
  })

  it('shows feedback newest first with dates', async () => {
    await renderTab()

    const items = screen.getAllByRole('listitem').filter((item) => item.textContent?.startsWith('Feedback'))
    expect(items.map((item) => item.querySelector('p')?.textContent)).toEqual([
      'Feedback 0',
      'Feedback 1',
      'Feedback 2',
    ])
    expect(
      within(items[0]).getByText(new Date(Date.UTC(2026, 10, 30)).toLocaleDateString()),
    ).toBeInTheDocument()
    expect(screen.queryByText(/showing \d+ of/i)).not.toBeInTheDocument()
  })

  it('says how many are shown when feedback is capped', async () => {
    await renderTab(results({ response_count: 51, feedback_count: 51, feedback: feedback(50) }))

    expect(screen.getByText('Showing 50 of 51')).toBeInTheDocument()
  })

  it('shows an empty state when nobody has answered', async () => {
    vi.mocked(getSurveyResults).mockResolvedValue(
      results({ response_count: 0, feedback_count: 0, feedback: [], top_skills: [], suggested_skills: [] }),
    )

    render(<SurveyResultsTab />)

    expect(await screen.findByText('No survey responses yet.')).toBeInTheDocument()
    expect(screen.queryByText('Ratings')).not.toBeInTheDocument()
  })

  it('shows a loading state while waiting', () => {
    vi.mocked(getSurveyResults).mockReturnValue(new Promise(() => {}))

    render(<SurveyResultsTab />)

    expect(screen.getByText('Loading survey results...')).toBeInTheDocument()
  })

  it("shows the backend's message when the request fails", async () => {
    vi.mocked(getSurveyResults).mockRejectedValue(
      new ApiError(403, {}, 'You do not have permission to perform this action.'),
    )

    render(<SurveyResultsTab />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You do not have permission to perform this action.',
    )
  })
})
