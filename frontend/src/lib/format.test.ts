import { describe, expect, it } from 'vitest'
import { attentionHeadline, daysAgo, initials, shortDate } from './format'

describe('attentionHeadline', () => {
  it('reads naturally for common counts', () => {
    expect(attentionHeadline(4, 2)).toBe('Four accounts need you today, and two more this week.')
    expect(attentionHeadline(1, 0)).toBe('One account needs you today.')
    expect(attentionHeadline(0, 3)).toBe('Three accounts could use a nudge this week.')
    expect(attentionHeadline(0, 0)).toBe('Nobody needs chasing today.')
  })
})

describe('dates', () => {
  it('formats ISO days without timezone drift', () => {
    expect(shortDate('2026-08-31')).toBe('Aug 31')
    expect(shortDate('2025-11-03', '2026-09-01')).toBe('Nov 3, 2025')
  })

  it('describes recency', () => {
    expect(daysAgo(1)).toBe('Yesterday')
    expect(daysAgo(9)).toBe('9 days ago')
    expect(daysAgo(65)).toBe('2 months ago')
  })
})

it('builds initials from company names', () => {
  expect(initials('Oak & Pine Family Dental')).toBe('OP')
})
