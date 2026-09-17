import { NavLink, Outlet } from 'react-router-dom'
import { CalendarCheck2, ListChecks, RotateCcw, Sun, Users } from 'lucide-react'
import { useDashboard, useResetDemo, useSystem } from '../api/hooks'
import { AccountPanel } from './account/AccountPanel'
import { useToast } from './toastContext'
import { cx } from '../lib/styles'
import { useAccountPanel } from './useAccountPanel'

const NAV = [
  { to: '/', label: 'Today', icon: Sun, end: true },
  { to: '/accounts', label: 'Accounts', icon: Users, end: false },
  { to: '/follow-ups', label: 'Follow-ups', icon: ListChecks, end: false },
]

export function AppLayout() {
  const { accountId } = useAccountPanel()
  const { data: dashboard } = useDashboard()
  const openCount = dashboard ? dashboard.level_counts.act_now + dashboard.level_counts.this_week : undefined

  return (
    <div className="min-h-screen lg:flex">
      <aside className="border-b border-line bg-surface lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-60 lg:flex-col lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-2.5 px-5 py-4 lg:py-6">
          <img src="/favicon.svg" alt="" className="size-7" />
          <div>
            <p className="text-[15px] font-bold leading-none">Relay</p>
            <p className="mt-1 text-xs text-ink-faint">Relationship assistant</p>
          </div>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:pb-0">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cx(
                  'flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium',
                  isActive ? 'bg-harbor-soft text-harbor' : 'text-ink-soft hover:bg-paper hover:text-ink',
                )
              }
            >
              <Icon className="size-4" aria-hidden />
              {label}
              {label === 'Follow-ups' && openCount !== undefined && openCount > 0 && (
                <span className="ml-auto rounded-full bg-act px-1.5 text-xs font-semibold text-white">{openCount}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <SidebarFooter />
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 lg:py-10">
          <Outlet />
        </div>
      </main>

      {accountId && <AccountPanel key={accountId} accountId={accountId} />}
    </div>
  )
}

function SidebarFooter() {
  const { data: system } = useSystem()
  const reset = useResetDemo()
  const toast = useToast()

  return (
    <div className="mt-auto hidden space-y-3 border-t border-line px-5 py-5 text-xs text-ink-soft lg:block">
      {system && (
        <div className="space-y-1">
          <p className="flex items-center gap-1.5">
            <CalendarCheck2 className="size-3.5" aria-hidden />
            Demo date: {system.today}
          </p>
          <p>
            {system.ai_mode === 'llm' ? (
              <>
                AI briefs: <span className="font-semibold text-ink">{system.model}</span>
              </>
            ) : (
              <>
                AI briefs: <span className="font-semibold text-ink">rules mode</span>
                <span className="block text-ink-faint">Add LLM_API_KEY to use a model.</span>
              </>
            )}
          </p>
        </div>
      )}
      <button
        type="button"
        className="inline-flex items-center gap-1.5 font-medium text-ink-soft hover:text-ink disabled:opacity-50"
        disabled={reset.isPending}
        onClick={() =>
          reset.mutate(undefined, { onSuccess: () => toast({ message: 'Demo data restored to the sample dataset.' }) })
        }
      >
        <RotateCcw className="size-3.5" aria-hidden />
        Reset demo data
      </button>
    </div>
  )
}
