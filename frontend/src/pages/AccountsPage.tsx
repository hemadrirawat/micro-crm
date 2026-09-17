import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useAccounts } from '../api/hooks'
import type { AccountSort, AccountView } from '../api/types'
import { useAccountPanel } from '../components/useAccountPanel'
import { EmptyState, ErrorState, HealthIndicator, ListSkeleton, PriorityPill, StatusTag } from '../components/ui'
import { cx } from '../lib/styles'
import { daysAgo, shortDate } from '../lib/format'

const VIEWS: { value: AccountView; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'needs_attention', label: 'Needs attention' },
  { value: 'prospects', label: 'Prospects' },
  { value: 'customers', label: 'Customers' },
]

const SORTS: { value: AccountSort; label: string }[] = [
  { value: 'priority', label: 'Priority' },
  { value: 'last_interaction', label: 'Last interaction' },
  { value: 'status', label: 'Status' },
  { value: 'name', label: 'Name' },
]

function useDebounced<T>(value: T, ms = 200): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms)
    return () => window.clearTimeout(id)
  }, [value, ms])
  return debounced
}

export function AccountsPage() {
  const [params, setParams] = useSearchParams()
  const view = (params.get('view') as AccountView | null) ?? 'all'
  const sort = (params.get('sort') as AccountSort | null) ?? 'priority'
  const [query, setQuery] = useState(params.get('q') ?? '')
  const debouncedQuery = useDebounced(query)
  const { data, isPending, error, refetch, isFetching } = useAccounts(view, debouncedQuery, sort)
  const { open } = useAccountPanel()

  const update = (key: string, value: string, fallback: string) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value === fallback) next.delete(key)
      else next.set(key, value)
      return next
    })

  // Keep the search in the URL (debounced) so a filtered view can be shared or reloaded.
  useEffect(() => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (debouncedQuery) next.set('q', debouncedQuery)
        else next.delete('q')
        return next
      },
      { replace: true },
    )
  }, [debouncedQuery, setParams])

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Accounts</h1>
        <p className="mt-1 text-ink-soft">Every prospect and customer, with what the relationship needs next.</p>
      </header>

      <div className="flex flex-col gap-3 md:flex-row md:items-center">
        <label className="relative flex-1">
          <span className="sr-only">Search accounts</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by practice or contact name"
            className="h-10 w-full rounded-lg border border-line-strong bg-surface pl-9 pr-3 text-sm placeholder:text-ink-faint"
          />
        </label>
        <div role="radiogroup" aria-label="Filter accounts" className="flex overflow-x-auto rounded-lg border border-line-strong bg-surface p-0.5">
          {VIEWS.map((v) => (
            <button
              key={v.value}
              type="button"
              role="radio"
              aria-checked={view === v.value}
              onClick={() => update('view', v.value, 'all')}
              className={cx(
                'shrink-0 rounded-md px-3 py-1.5 text-sm font-medium',
                view === v.value ? 'bg-harbor text-white' : 'text-ink-soft hover:text-ink',
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-soft">
          Sort by
          <select
            value={sort}
            onChange={(e) => update('sort', e.target.value, 'priority')}
            className="h-10 rounded-lg border border-line-strong bg-surface px-2 text-sm text-ink"
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isPending ? (
        <ListSkeleton rows={6} />
      ) : data.length === 0 ? (
        <EmptyState
          title={debouncedQuery ? `No accounts match “${debouncedQuery}”` : 'No accounts in this view'}
          action={
            <button type="button" className="text-sm font-semibold text-harbor" onClick={() => {
              setQuery('')
              update('view', 'all', 'all')
            }}>
              Show all accounts
            </button>
          }
        >
          Try a practice name or a contact’s first name.
        </EmptyState>
      ) : (
        <div className={cx('overflow-hidden rounded-xl border border-line bg-surface transition-opacity', isFetching && 'opacity-70')}>
          <table className="w-full text-left text-sm">
            <thead className="hidden border-b border-line bg-paper/60 text-xs text-ink-soft md:table-header-group">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium">Account</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Priority</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Why, and what next</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Last contact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.map(({ customer, insight, primary_contact }) => (
                <tr
                  key={customer.id}
                  onClick={() => open(customer.id)}
                  className="grid cursor-pointer gap-2 px-4 py-3 hover:bg-paper/70 md:table-row md:p-0"
                >
                  <td className="md:px-4 md:py-3 md:align-top">
                    <button type="button" className="text-left font-semibold hover:text-harbor" onClick={(e) => {
                      e.stopPropagation()
                      open(customer.id)
                    }}>
                      {customer.name}
                    </button>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <StatusTag status={customer.status} />
                      <HealthIndicator health={insight.relationship_health} />
                    </div>
                    {primary_contact && (
                      <p className="mt-1 text-xs text-ink-faint">
                        {primary_contact.name}, {primary_contact.role}
                      </p>
                    )}
                  </td>
                  <td className="md:px-4 md:py-3 md:align-top">
                    <PriorityPill level={insight.priority_level} score={insight.priority_score} onHold={insight.on_hold} />
                  </td>
                  <td className="md:max-w-md md:px-4 md:py-3 md:align-top">
                    <p className="text-ink-soft">{insight.reason}</p>
                    <p className="mt-1 font-semibold text-harbor">{insight.suggested_action.title}</p>
                  </td>
                  <td className="whitespace-nowrap text-ink-soft md:px-4 md:py-3 md:align-top">
                    {insight.last_interaction_at ? (
                      <>
                        {shortDate(insight.last_interaction_at)}
                        <span className="block text-xs text-ink-faint">
                          {daysAgo(insight.days_since_last_interaction)}
                        </span>
                      </>
                    ) : (
                      'None yet'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
