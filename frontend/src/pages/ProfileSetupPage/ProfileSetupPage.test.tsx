import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ProfileSetupPage from './ProfileSetupPage'
import { logout } from '../../lib/api/auth'

const navigateMock = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

vi.mock('../../lib/api/auth', () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}))

const COURSES = [
  { code: 'CS 151', name: 'Introduction to Programming with Java' },
  { code: 'CS 361', name: 'Data Structures and Algorithms' },
]

const SKILL_GROUPS = [
  {
    key: 'language',
    name: 'Main language',
    points: 8.62,
    tools: [
      { name: 'Python', label: 'Python' },
      { name: 'Oracle Java', label: 'Java' },
    ],
  },
  {
    key: 'databases',
    name: 'Databases',
    points: 7.76,
    tools: [{ name: 'Structured query language SQL', label: 'SQL' }],
  },
]

const CERTIFICATES = ['AWS Certified Cloud Practitioner', 'CompTIA Security+']

const LEVELS = [
  { value: 'beginner', label: 'Learning', credit: 0.25 },
  { value: 'intermediate', label: 'Practicing', credit: 0.6 },
  { value: 'expert', label: 'Project ready', credit: 1 },
]

async function fillAboutYou(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText(/student id/i), 'S123')
  await user.selectOptions(screen.getByLabelText(/university/i), 'Old Dominion University')
  await user.selectOptions(screen.getByLabelText(/major/i), 'Computer Science')
  await user.selectOptions(screen.getByLabelText(/location/i), 'Norfolk, VA')
  await user.selectOptions(screen.getByLabelText(/target role/i), 'Software Developer')
}

function postedBodies(path: string) {
  return vi
    .mocked(fetch)
    .mock.calls.filter(
      ([url, options]) => options?.method === 'POST' && (url as string).endsWith(path),
    )
    .map(([, options]) => JSON.parse(options?.body as string))
}

// A student who already has a profile, for edit mode
type Existing = {
  profile: Record<string, unknown>
  classes: Record<string, unknown>[]
  skills: Record<string, unknown>[]
  certificates: Record<string, unknown>[]
}

const json = (body: unknown, status = 200) =>
  Promise.resolve({
    ok: status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(body == null ? '' : JSON.stringify(body)),
  })

// Writes succeed (POSTs return a new id); GETs of the profile and its
// records return `existing`, or 404 when there's no profile yet.
function stubMe(firstName: string | null, existing?: Existing) {
  return vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    const method = options?.method ?? 'GET'
    if (method === 'DELETE') return json(null, 204)
    if (method !== 'GET') return json({ id: 'new-id' }, method === 'POST' ? 201 : 200)
    if (url.endsWith('/api/auth/profile/')) {
      return existing ? json(existing.profile) : json({ detail: 'Not found.' }, 404)
    }
    for (const kind of ['classes', 'skills', 'certificates'] as const) {
      if (url.endsWith(`/api/auth/profile/${kind}/`)) {
        return json({ results: existing?.[kind] ?? [] })
      }
    }
    if (url.includes('/api/benchmark/demo/options/')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            courses: COURSES,
            skill_groups: SKILL_GROUPS,
            levels: LEVELS,
            certificates: CERTIFICATES,
          }),
      })
    }
    if (url.includes('/api/auth/me')) {
      return firstName
        ? Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ first_name: firstName }),
          })
        : Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve(null) })
    }
    return json({})
  })
}

function requests(method: string) {
  return vi
    .mocked(fetch)
    .mock.calls.filter(([, options]) => (options?.method ?? 'GET') === method)
    .map(([url, options]) => ({
      url: (url as string).replace(/^.*(\/api\/)/, '$1'),
      body: options?.body ? JSON.parse(options.body as string) : undefined,
    }))
}

describe('ProfileSetupPage', () => {
  beforeEach(() => {
    localStorage.clear()
    navigateMock.mockClear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('greets the user by their first name once /api/auth/me resolves', async () => {
    vi.stubGlobal('fetch', stubMe('ada'))

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Hi Ada, welcome to GradPace' })).toBeInTheDocument()
  })

  it('submits the profile form with the access token and navigates to /profile', async () => {
    vi.stubGlobal('fetch', stubMe(null))
    localStorage.setItem('access', 'my-token')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await user.type(await screen.findByLabelText(/student id/i), 'S123')
    await user.selectOptions(screen.getByLabelText(/university/i), 'Old Dominion University')
    await user.selectOptions(screen.getByLabelText(/major/i), 'Computer Science')
    await user.selectOptions(screen.getByLabelText(/location/i), 'Norfolk, VA')
    await user.selectOptions(screen.getByLabelText(/target role/i), 'Software Developer')
    await user.click(screen.getByRole('button', { name: /create profile/i }))

    expect(navigateMock).toHaveBeenCalledWith('/profile', { replace: true })
    const profileCall = vi
      .mocked(fetch)
      .mock.calls.find(
        ([url, options]) =>
          options?.method === 'POST' && (url as string).endsWith('/api/auth/profile/'),
      )
    const [, options] = profileCall!
    expect(options?.headers).toMatchObject({ Authorization: 'Bearer my-token' })
    expect(JSON.parse(options?.body as string)).toMatchObject({
      student_id: 'S123',
      uni: 'Old Dominion University',
      major: 'Computer Science',
      location: 'Norfolk, VA',
      target_job: '15-1252',
    })
  })

  it('lists the courses and saves the checked ones after the profile', async () => {
    vi.stubGlobal('fetch', stubMe(null))
    localStorage.setItem('access', 'my-token')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await user.type(await screen.findByLabelText(/student id/i), 'S123')
    await user.selectOptions(screen.getByLabelText(/university/i), 'Old Dominion University')
    await user.selectOptions(screen.getByLabelText(/major/i), 'Computer Science')
    await user.selectOptions(screen.getByLabelText(/location/i), 'Norfolk, VA')
    await user.selectOptions(screen.getByLabelText(/target role/i), 'Software Developer')

    // Multi-select dropdown: pick two, then remove one from the list below
    const dropdown = await screen.findByRole('button', { name: /^courses$/i })
    expect(screen.queryByRole('checkbox', { name: /CS 361/ })).not.toBeInTheDocument()
    await user.click(dropdown)
    await user.click(screen.getByRole('checkbox', { name: /CS 151/ }))
    await user.click(screen.getByRole('checkbox', { name: /CS 361/ }))
    expect(dropdown).toHaveTextContent('CS 151, CS 361')
    await user.click(screen.getByRole('button', { name: 'Remove CS 151' }))

    await user.selectOptions(screen.getByLabelText('CS 361 semester'), 'spring')
    await user.clear(screen.getByLabelText('CS 361 year'))
    await user.type(screen.getByLabelText('CS 361 year'), '2025')
    expect(screen.getByText('1 of 2 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /create profile/i }))

    const posts = vi
      .mocked(fetch)
      .mock.calls.filter(([, options]) => options?.method === 'POST')
      .map(([url, options]) => [url as string, JSON.parse(options?.body as string)])
    expect(posts.map(([url]) => url)).toEqual([
      expect.stringContaining('/api/auth/profile/'),
      expect.stringContaining('/api/auth/profile/classes/'),
    ])
    expect(posts[1][1]).toEqual({
      course_code: 'CS 361',
      course_name: 'Data Structures and Algorithms',
      semester: 'spring',
      year: 2025,
    })
    expect(navigateMock).toHaveBeenCalledWith('/profile', { replace: true })
  })

  it('saves each picked skill with its level after the profile', async () => {
    vi.stubGlobal('fetch', stubMe(null))
    localStorage.setItem('access', 'my-token')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await fillAboutYou(user)

    // Main language: pick Python and Java, set Python to Project ready, drop Java
    const language = await screen.findByRole('button', { name: /^main language/i })
    await user.click(language)
    await user.click(screen.getByRole('checkbox', { name: 'Python' }))
    await user.click(screen.getByRole('checkbox', { name: 'Java' }))
    expect(language).toHaveTextContent('Python, Java')
    const python = screen.getByRole('group', { name: 'Python level' })
    expect(within(python).getByRole('button', { name: 'Learning' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await user.click(within(python).getByRole('button', { name: 'Project ready' }))
    await user.click(screen.getByRole('button', { name: 'Remove Java' }))

    // Databases: SQL at the default level (Learning)
    await user.click(screen.getByRole('button', { name: /^databases/i }))
    await user.click(screen.getByRole('checkbox', { name: 'SQL' }))

    await user.click(screen.getByRole('button', { name: /create profile/i }))

    expect(postedBodies('/api/auth/profile/')).toHaveLength(1)
    expect(postedBodies('/api/auth/profile/skills/')).toEqual([
      { name: 'Python', proficiency_level: 'expert' },
      { name: 'Structured query language SQL', proficiency_level: 'beginner' },
    ])
    expect(navigateMock).toHaveBeenCalledWith('/profile', { replace: true })
  })

  it('saves each picked certificate with its issuer after the profile', async () => {
    vi.stubGlobal('fetch', stubMe(null))
    localStorage.setItem('access', 'my-token')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await fillAboutYou(user)
    await user.click(await screen.findByRole('button', { name: /^certificates$/i }))
    await user.click(screen.getByRole('checkbox', { name: 'AWS Certified Cloud Practitioner' }))
    await user.click(screen.getByRole('checkbox', { name: 'CompTIA Security+' }))
    await user.click(screen.getByRole('button', { name: 'Remove AWS Certified Cloud Practitioner' }))
    await user.click(screen.getByRole('button', { name: /create profile/i }))

    expect(postedBodies('/api/auth/profile/certificates/')).toEqual([
      { name: 'CompTIA Security+', issuing_organization: 'CompTIA' },
    ])
    expect(navigateMock).toHaveBeenCalledWith('/profile', { replace: true })
  })

  it('edits an existing profile: loads saved records and sends only the changes', async () => {
    vi.stubGlobal(
      'fetch',
      stubMe('ada', {
        profile: {
          student_id: 'S123',
          uni: 'Old Dominion University',
          major: 'Computer Science',
          location: 'Norfolk, VA',
          target_job: '15-1252',
        },
        classes: [{ id: 'c1', course_code: 'CS 151', semester: 'fall', year: 2024 }],
        skills: [
          { id: 's1', name: 'Python', proficiency_level: 'advanced' },
          { id: 's2', name: 'Structured query language SQL', proficiency_level: 'expert' },
        ],
        certificates: [{ id: 'k1', name: 'AWS Certified Cloud Practitioner' }],
      }),
    )
    localStorage.setItem('access', 'my-token')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    // Saved data is loaded into the form
    expect(
      await screen.findByRole('heading', { name: 'Update your profile, Ada' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/student id/i)).toHaveValue('S123')
    expect(screen.getByLabelText(/student id/i)).toBeDisabled()
    expect(screen.getByLabelText(/university/i)).toHaveValue('Old Dominion University')
    expect(screen.getByLabelText(/target role/i)).toHaveValue('15-1252')
    expect(await screen.findByLabelText('CS 151 year')).toHaveValue(2024)
    const python = screen.getByRole('group', { name: 'Python level' })
    // 'advanced' shows as Practicing
    expect(within(python).getByRole('button', { name: 'Practicing' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )

    // Change things
    await user.click(within(python).getByRole('button', { name: 'Project ready' }))
    await user.click(screen.getByRole('button', { name: 'Remove SQL' }))
    await user.clear(screen.getByLabelText('CS 151 year'))
    await user.type(screen.getByLabelText('CS 151 year'), '2023')
    await user.click(screen.getByRole('button', { name: /^courses$/i }))
    await user.click(screen.getByRole('checkbox', { name: /CS 361/ }))
    await user.click(screen.getByRole('button', { name: 'Remove AWS Certified Cloud Practitioner' }))
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(requests('POST')).toEqual([
      {
        url: '/api/auth/profile/classes/',
        body: {
          course_code: 'CS 361',
          course_name: 'Data Structures and Algorithms',
          semester: expect.any(String),
          year: expect.any(Number),
        },
      },
    ])
    expect(requests('PATCH')).toEqual([
      {
        url: '/api/auth/profile/',
        body: {
          uni: 'Old Dominion University',
          major: 'Computer Science',
          location: 'Norfolk, VA',
          target_job: '15-1252',
        },
      },
      { url: '/api/auth/profile/classes/c1/', body: { semester: 'fall', year: 2023 } },
      { url: '/api/auth/profile/skills/s1/', body: { proficiency_level: 'expert' } },
    ])
    expect(requests('DELETE').map((r) => r.url)).toEqual([
      '/api/auth/profile/skills/s2/',
      '/api/auth/profile/certificates/k1/',
    ])
    expect(navigateMock).toHaveBeenCalledWith('/profile', { replace: true })
  })

  it('redirects to /login when not logged in', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => json({ detail: 'Not authenticated.' }, 401)),
    )

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith('/login', { replace: true }),
    )
  })

  it('logs out and redirects to /login when "Log out" is clicked', async () => {
    vi.stubGlobal('fetch', stubMe(null))
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: /log out/i }))

    expect(logout).toHaveBeenCalledTimes(1)
    expect(navigateMock).toHaveBeenCalledWith('/login', { replace: true })
  })
})
