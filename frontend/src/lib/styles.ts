import type { PriorityLevel } from '../api/types'

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

export const LEVEL_STYLES: Record<PriorityLevel, { pill: string; bar: string; text: string }> = {
  act_now: { pill: 'bg-act-soft text-act', bar: 'bg-act', text: 'text-act' },
  this_week: { pill: 'bg-week-soft text-week', bar: 'bg-week', text: 'text-week' },
  check_in: { pill: 'bg-checkin-soft text-checkin', bar: 'bg-checkin', text: 'text-checkin' },
  monitor: { pill: 'bg-monitor-soft text-monitor', bar: 'bg-line-strong', text: 'text-monitor' },
}
