import type { AccountStatus, Health, Intent, InteractionType, PriorityLevel } from '../api/types'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

/** Dates from the API are plain ISO days; parse them without timezone drift. */
export function parseDay(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function shortDate(iso: string, today?: string): string {
  const date = parseDay(iso)
  const sameYear = !today || parseDay(today).getFullYear() === date.getFullYear()
  return `${MONTHS[date.getMonth()]} ${date.getDate()}${sameYear ? '' : `, ${date.getFullYear()}`}`
}

export function longDate(iso: string): string {
  const date = parseDay(iso)
  return `${WEEKDAYS[date.getDay()]}, ${MONTHS[date.getMonth()]} ${date.getDate()}`
}

export function daysAgo(days: number | null): string {
  if (days === null) return 'No contact yet'
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 14) return `${days} days ago`
  if (days < 60) return `${Math.round(days / 7)} weeks ago`
  return `${Math.round(days / 30)} months ago`
}

const NUMBER_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten']

export function countWord(n: number): string {
  return NUMBER_WORDS[n] ?? String(n)
}

export function plural(n: number, singular: string, pluralForm = `${singular}s`): string {
  return n === 1 ? singular : pluralForm
}

/** The dashboard headline, e.g. "Four accounts need you today, and two more this week." */
export function attentionHeadline(actNow: number, thisWeek: number): string {
  if (actNow === 0 && thisWeek === 0) return 'Nobody needs chasing today.'
  if (actNow === 0) {
    return `${countWord(thisWeek)} ${plural(thisWeek, 'account')} could use a nudge this week.`
  }
  const lead = `${countWord(actNow)} ${plural(actNow, 'account')} ${actNow === 1 ? 'needs' : 'need'} you today`
  if (thisWeek === 0) return `${lead}.`
  return `${lead}, and ${countWord(thisWeek).toLowerCase()} more this week.`
}

export function greeting(hour: number): string {
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

export const LEVEL_LABEL: Record<PriorityLevel, string> = {
  act_now: 'Act today',
  this_week: 'This week',
  check_in: 'Check in',
  monitor: 'No action',
}

export const HEALTH_LABEL: Record<Health, string> = {
  healthy: 'Healthy',
  watch: 'Watch',
  at_risk: 'At risk',
}

export const INTENT_LABEL: Record<Intent, string> = {
  high: 'High intent',
  medium: 'Some interest',
  low: 'Early interest',
  unknown: 'Intent unclear',
  existing_customer: 'Customer',
}

export const STATUS_LABEL: Record<AccountStatus, string> = {
  prospect: 'Prospect',
  customer: 'Customer',
}

export const TYPE_LABEL: Record<InteractionType, string> = {
  email: 'Email',
  call: 'Call',
  meeting: 'Meeting',
  note: 'Note',
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter((w) => /^[A-Za-z]/.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')
}
