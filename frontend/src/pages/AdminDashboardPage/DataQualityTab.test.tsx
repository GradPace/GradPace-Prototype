import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DataQualityTab from './DataQualityTab'
import { getDataHealth, type DataHealth, type OccupationHealth } from '../../lib/api/admin'
import { ApiError } from '../../lib/api/api'

vi.mock('../../lib/api/admin', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/api/admin')>()),
  getDataHealth: vi.fn(),
}))

function job(overrides: Partial<OccupationHealth>): OccupationHealth {
  return {
    soc_code: '15-0000',
    title: 'Job',
    source: 'official',
    posting_count: 5,
    skill_count: 4,
    median_annual_wage: 100000,
    few_postings: false,
    missing_wage: false,
    no_skills: false,
    ...overrides,
  }
}

// Backend order is soc_code - the clean job comes first here, so the
// flagged-first sort is visible.
const CLEAN = job({ soc_code: '15-1111', title: 'Clean Job' })
const FEW = job({ soc_code: '15-2222', title: 'Few Job', posting_count: 2, few_postings: true })
const NO_WAGE = job({
  soc_code: '15-3333',
  title: 'No Wage Job',
  source: 'bls',
  median_annual_wage: null,
  missing_wage: true,
})
const NO_SKILLS = job({ soc_code: '15-4444', title: 'No Skills Job', skill_count: 0, no_skills: true })

function report(overrides: Partial<DataHealth> = {}): DataHealth {
  return {
    totals: {
      jobs: { total: 25, by_source: { official: 24, generated: 0, bls: 1 } },
      skills: { total: 900 },
      postings: { total: 400, by_source: { generated: 400 } },
    },
    catalog_updated_at: '2026-11-20T14:03:11Z',
    occupations: [CLEAN, FEW, NO_WAGE, NO_SKILLS],
    student_locations: {
      profiles: 6,
      with_location: 4,
      recognized: 1,
      unrecognized: 3,
      unrecognized_values: [
        { location: 'Narfolk', count: 2 },
        { location: 'Nowhere, ZZ', count: 1 },
      ],
    },
    ...overrides,
  }
}

function tile(label: string) {
  // The tile's label is a <p>; "Skills" is also a table header.
  return within(screen.getByText(label, { selector: 'p' }).parentElement as HTMLElement)
}

function rowFor(title: string) {
  return within(screen.getByText(title).closest('tr') as HTMLElement)
}

function occupationTitles() {
  const table = screen.getByText('SOC code').closest('table') as HTMLElement
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map((row) => (row as HTMLTableRowElement).cells[1].textContent)
}

async function renderTab(data: DataHealth = report()) {
  vi.mocked(getDataHealth).mockResolvedValue(data)
  render(<DataQualityTab />)
  await screen.findByText('Occupations')
}

describe('DataQualityTab', () => {
  beforeEach(() => {
    vi.mocked(getDataHealth).mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows totals with every source, including unexpected ones', async () => {
    await renderTab()

    const jobs = tile('Jobs')
    expect(jobs.getByText('25')).toBeInTheDocument()
    expect(jobs.getByText('official 24')).toBeInTheDocument()
    expect(jobs.getByText('generated 0')).toBeInTheDocument()
    expect(jobs.getByText('bls 1')).toBeInTheDocument()
    expect(tile('Skills').getByText('900')).toBeInTheDocument()
    const postings = tile('Postings')
    expect(postings.getByText('400')).toBeInTheDocument()
    expect(postings.getByText('generated 400')).toBeInTheDocument()
  })

  it('shows when the catalog was last seeded', async () => {
    await renderTab()

    expect(
      tile('Catalog last seeded or edited').getByText(
        new Date('2026-11-20T14:03:11Z').toLocaleString(),
      ),
    ).toBeInTheDocument()
  })

  it('shows Never when the catalog has never been seeded', async () => {
    await renderTab(report({ catalog_updated_at: null }))

    expect(tile('Catalog last seeded or edited').getByText('Never')).toBeInTheDocument()
  })

  it('puts each flag badge on the right row', async () => {
    await renderTab()

    expect(rowFor('Few Job').getByText('Few postings')).toBeInTheDocument()
    expect(rowFor('No Wage Job').getByText('Missing wage')).toBeInTheDocument()
    expect(rowFor('No Wage Job').getByText('—')).toBeInTheDocument()
    expect(rowFor('No Skills Job').getByText('No skills')).toBeInTheDocument()
    expect(rowFor('Few Job').queryByText('Missing wage')).not.toBeInTheDocument()
    const clean = rowFor('Clean Job')
    expect(clean.getByText('$100,000')).toBeInTheDocument()
    for (const flag of ['Few postings', 'Missing wage', 'No skills']) {
      expect(clean.queryByText(flag)).not.toBeInTheDocument()
    }
  })

  it('sorts flagged rows first, and the toggle shows only them', async () => {
    const user = userEvent.setup()
    await renderTab()

    expect(occupationTitles()).toEqual(['Few Job', 'No Wage Job', 'No Skills Job', 'Clean Job'])

    await user.click(screen.getByRole('checkbox', { name: /show only flagged/i }))
    expect(occupationTitles()).toEqual(['Few Job', 'No Wage Job', 'No Skills Job'])

    await user.click(screen.getByRole('checkbox', { name: /show only flagged/i }))
    expect(occupationTitles()).toContain('Clean Job')
  })

  it('says when no occupation is flagged and the toggle is on', async () => {
    const user = userEvent.setup()
    await renderTab(report({ occupations: [CLEAN] }))

    await user.click(screen.getByRole('checkbox', { name: /show only flagged/i }))

    expect(screen.getByText('No flagged occupations.')).toBeInTheDocument()
  })

  it('shows student location counts and the unrecognized values', async () => {
    await renderTab()

    expect(screen.getByText('1 of 4')).toBeInTheDocument()
    expect(screen.getByText('2 profiles have no location')).toBeInTheDocument()
    expect(screen.getByText(/can't be used for event distance/i)).toBeInTheDocument()
    expect(rowFor('Narfolk').getByText('2')).toBeInTheDocument()
    expect(rowFor('Nowhere, ZZ').getByText('1')).toBeInTheDocument()
  })

  it('says when every saved location is recognized', async () => {
    await renderTab(
      report({
        student_locations: {
          profiles: 2,
          with_location: 2,
          recognized: 2,
          unrecognized: 0,
          unrecognized_values: [],
        },
      }),
    )

    expect(screen.getByText('Every saved location is recognized.')).toBeInTheDocument()
  })

  it('shows an empty catalog message', async () => {
    await renderTab(
      report({
        totals: {
          jobs: { total: 0, by_source: { official: 0, generated: 0 } },
          skills: { total: 0 },
          postings: { total: 0, by_source: { generated: 0 } },
        },
        catalog_updated_at: null,
        occupations: [],
      }),
    )

    expect(screen.getByText(/job catalog is empty/i)).toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('shows a loading state while waiting', () => {
    vi.mocked(getDataHealth).mockReturnValue(new Promise(() => {}))

    render(<DataQualityTab />)

    expect(screen.getByText('Loading data quality...')).toBeInTheDocument()
  })

  it("shows the backend's message when the request fails", async () => {
    vi.mocked(getDataHealth).mockRejectedValue(
      new ApiError(403, {}, 'You do not have permission to perform this action.'),
    )

    render(<DataQualityTab />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You do not have permission to perform this action.',
    )
  })
})
