import type { AccountListItem, Dashboard } from '../api/types'
import { useDashboard } from '../api/hooks'
import { AccountRow } from '../components/AccountRow'
import { useAccountPanel } from '../components/useAccountPanel'
import { EmptyState, ErrorState, ListSkeleton, SectionTitle, Skeleton } from '../components/ui'
import { cx } from '../lib/styles'
import { HEALTH_LABEL, TYPE_LABEL, attentionHeadline, greeting, longDate, shortDate } from '../lib/format'

export function TodayPage() {
  const { data, isPending, error, refetch } = useDashboard()

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />

  return (
    <div className="space-y-10">
      <header className="max-w-3xl">
        {isPending ? (
          <>
            <Skeleton className="h-4 w-48" />
            <Skeleton className="mt-3 h-10 w-full" />
          </>
        ) : (
          <>
            <p className="text-sm text-ink-soft">
              {longDate(data.today)}. {greeting(new Date().getHours())}.
            </p>
            <h1 className="mt-2 text-3xl font-semibold leading-tight tracking-tight text-balance sm:text-[2.5rem]">
              {attentionHeadline(data.level_counts.act_now, data.level_counts.this_week)}
            </h1>
            <p className="mt-3 text-ink-soft">
              Ranked by what’s waiting on you: open asks, deadlines, stalled deals and quiet relationships.
            </p>
          </>
        )}
      </header>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="space-y-10">
          <section aria-labelledby="needs-attention">
            <SectionTitle id="needs-attention" aside={data && `${data.needs_attention.length} accounts`}>
              Needs your attention
            </SectionTitle>
            {isPending ? (
              <ListSkeleton />
            ) : data.needs_attention.length === 0 ? (
              <EmptyState title="You’re all caught up">
                No open asks, deadlines or stalled deals. Check the opportunities below when you have time.
              </EmptyState>
            ) : (
              <Queue items={data.needs_attention} ranked />
            )}
          </section>

          {data && data.opportunities.length > 0 && (
            <section aria-labelledby="opportunities">
              <SectionTitle id="opportunities" aside="Not urgent, worth a touch">
                Relationship opportunities
              </SectionTitle>
              <Queue items={data.opportunities} />
            </section>
          )}

          {data && data.on_hold.length > 0 && (
            <section aria-labelledby="no-action">
              <SectionTitle id="no-action" aside="Deliberately left alone">
                No action needed
              </SectionTitle>
              <Queue items={data.on_hold} compact />
            </section>
          )}
        </div>

        <aside className="space-y-8">{data ? <SideColumn data={data} /> : <ListSkeleton rows={2} />}</aside>
      </div>
    </div>
  )
}

function Queue({ items, ranked, compact }: { items: AccountListItem[]; ranked?: boolean; compact?: boolean }) {
  return (
    <ol className="space-y-2.5">
      {items.map((item, i) => (
        <AccountRow key={item.customer.id} item={item} rank={ranked ? i + 1 : undefined} compact={compact} />
      ))}
    </ol>
  )
}

const HEALTH_BAR = { healthy: 'bg-checkin', watch: 'bg-week', at_risk: 'bg-act' } as const

function SideColumn({ data }: { data: Dashboard }) {
  const { open } = useAccountPanel()
  const total = data.health.healthy + data.health.watch + data.health.at_risk

  return (
    <>
      <section aria-labelledby="health">
        <SectionTitle id="health">Relationship health</SectionTitle>
        <div className="rounded-xl border border-line bg-surface p-4">
          <p className="text-sm text-ink-soft">
            {data.prospects} prospects and {data.customers} customers
          </p>
          <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-paper" role="img"
            aria-label={`${data.health.healthy} healthy, ${data.health.watch} to watch, ${data.health.at_risk} at risk`}>
            {(['healthy', 'watch', 'at_risk'] as const).map((key) => (
              <span key={key} className={HEALTH_BAR[key]} style={{ width: `${(data.health[key] / total) * 100}%` }} />
            ))}
          </div>
          <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
            {(['healthy', 'watch', 'at_risk'] as const).map((key) => (
              <div key={key}>
                <dt className="flex items-center gap-1.5 text-xs text-ink-soft">
                  <span className={cx('size-2 rounded-full', HEALTH_BAR[key])} aria-hidden />
                  {HEALTH_LABEL[key]}
                </dt>
                <dd className="mt-0.5 text-lg font-semibold">{data.health[key]}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section aria-labelledby="recent">
        <SectionTitle id="recent">Recent activity</SectionTitle>
        <ul className="space-y-3">
          {data.recent_activity.map(({ interaction, customer_id, customer_name }) => (
            <li key={interaction.id}>
              <button type="button" onClick={() => open(customer_id)} className="group w-full text-left">
                <p className="text-xs text-ink-faint">
                  {shortDate(interaction.occurred_at)}, {TYPE_LABEL[interaction.type].toLowerCase()}
                </p>
                <p className="text-sm font-semibold group-hover:text-harbor">{customer_name}</p>
                <p className="line-clamp-2 text-sm text-ink-soft">{interaction.notes}</p>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
