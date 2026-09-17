import { Check } from 'lucide-react'
import { useAccounts, useDashboard } from '../api/hooks'
import type { AccountListItem, PriorityLevel } from '../api/types'
import { useAccountPanel } from '../components/useAccountPanel'
import { useMarkDone } from '../components/useMarkDone'
import { Button, EmptyState, ErrorState, ListSkeleton, SectionTitle, StatusTag } from '../components/ui'
import { LEVEL_STYLES, cx } from '../lib/styles'
import { shortDate } from '../lib/format'

const GROUPS: { level: PriorityLevel; title: string; hint: string }[] = [
  { level: 'act_now', title: 'Today', hint: 'Someone is waiting on you' },
  { level: 'this_week', title: 'This week', hint: 'Keep deals moving' },
  { level: 'check_in', title: 'When you have time', hint: 'Relationship upkeep' },
]

export function FollowUpsPage() {
  const accounts = useAccounts('all', '', 'priority')
  const dashboard = useDashboard()

  if (accounts.error) return <ErrorState error={accounts.error} onRetry={() => accounts.refetch()} />

  const open = (accounts.data ?? []).filter((a) => a.insight.open_follow_up)
  const completed = (dashboard.data?.recent_activity ?? []).filter(
    (a) => a.interaction.source === 'user' && a.interaction.notes.startsWith('Follow-up completed'),
  )

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Follow-ups</h1>
        <p className="mt-1 text-ink-soft">
          Every open follow-up the assistant found in your history. Marking one done logs it on the account.
        </p>
      </header>

      {accounts.isPending ? (
        <ListSkeleton />
      ) : open.length === 0 ? (
        <EmptyState title="No open follow-ups">
          Nothing is waiting on you. New asks will appear here as soon as they’re logged.
        </EmptyState>
      ) : (
        GROUPS.map(({ level, title, hint }) => {
          const items = open.filter((a) => a.insight.priority_level === level)
          if (items.length === 0) return null
          return (
            <section key={level} aria-label={title}>
              <SectionTitle aside={hint}>
                <span className="inline-flex items-center gap-2">
                  <span className={cx('size-2 rounded-full', LEVEL_STYLES[level].bar)} aria-hidden />
                  {title}
                </span>
              </SectionTitle>
              <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
                {items.map((item) => (
                  <FollowUpItem key={item.customer.id} item={item} />
                ))}
              </ul>
            </section>
          )
        })
      )}

      {completed.length > 0 && (
        <section aria-label="Recently completed">
          <SectionTitle>Recently completed</SectionTitle>
          <ul className="space-y-2">
            {completed.map(({ interaction, customer_name }) => (
              <li key={interaction.id} className="flex items-start gap-2 text-sm text-ink-soft">
                <Check className="mt-0.5 size-4 shrink-0 text-checkin" aria-hidden />
                <span>
                  <span className="font-semibold text-ink">{customer_name}</span>,{' '}
                  {shortDate(interaction.occurred_at)}: {interaction.notes.replace('Follow-up completed: ', '')}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function FollowUpItem({ item }: { item: AccountListItem }) {
  const { open } = useAccountPanel()
  const { markDone, pendingId } = useMarkDone()
  const others = item.insight.follow_ups.slice(1)

  return (
    <li className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => open(item.customer.id)} className="font-semibold hover:text-harbor">
            {item.customer.name}
          </button>
          <StatusTag status={item.customer.status} />
        </div>
        <p className="mt-1 font-semibold text-harbor">{item.insight.suggested_action.title}</p>
        <p className="mt-0.5 text-sm text-ink-soft">{item.insight.reason}</p>
        {others.length > 0 && (
          <p className="mt-1 text-xs text-ink-faint">
            Also open: {others.map((f) => f.title).join('; ')}
          </p>
        )}
      </div>
      <div className="flex shrink-0 gap-2">
        <Button size="sm" variant="ghost" onClick={() => open(item.customer.id)}>
          View account
        </Button>
        <Button
          size="sm"
          icon={<Check className="size-3.5" aria-hidden />}
          loading={pendingId === item.customer.id}
          onClick={() => markDone(item.customer.id, item.customer.name)}
        >
          Mark done
        </Button>
      </div>
    </li>
  )
}
