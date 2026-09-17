import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { useAccount, useSystem } from '../../api/hooks'
import { STATUS_LABEL, shortDate } from '../../lib/format'
import { ErrorState, HealthIndicator, PriorityPill, Skeleton, StatusTag } from '../ui'
import { useAccountPanel } from '../useAccountPanel'
import { BriefSection } from './BriefSection'
import { ContextSection } from './ContextSection'
import { Timeline } from './Timeline'

/** Account 360: a side panel so the queue stays one click away. */
export function AccountPanel({ accountId }: { accountId: string }) {
  const { close } = useAccountPanel()
  const { data, isPending, error, refetch } = useAccount(accountId)
  const { data: system } = useSystem()
  const closeButton = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeButton.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', onKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previousOverflow
    }
  }, [close])

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-ink/30" onClick={close} aria-hidden />
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="account-title"
        className="panel-enter relative flex h-full w-full max-w-3xl flex-col overflow-y-auto bg-paper shadow-2xl"
      >
        <header className="sticky top-0 z-10 border-b border-line bg-surface/95 px-5 py-4 backdrop-blur sm:px-8">
          <div className="flex items-start gap-4">
            <div className="min-w-0 flex-1">
              {isPending ? (
                <Skeleton className="h-7 w-64" />
              ) : data ? (
                <>
                  <h2 id="account-title" className="text-2xl font-semibold tracking-tight">
                    {data.customer.name}
                  </h2>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                    <StatusTag status={data.customer.status} />
                    <PriorityPill
                      level={data.insight.priority_level}
                      score={data.insight.priority_score}
                      onHold={data.insight.on_hold}
                    />
                    <HealthIndicator health={data.insight.relationship_health} />
                    <span className="text-xs text-ink-faint">
                      {STATUS_LABEL[data.customer.status]} since {shortDate(data.customer.created_at, system?.today)}
                    </span>
                  </div>
                </>
              ) : (
                <h2 id="account-title" className="text-xl font-semibold">Account</h2>
              )}
            </div>
            <button
              ref={closeButton}
              type="button"
              onClick={close}
              aria-label="Close account"
              className="rounded-lg p-1.5 text-ink-soft hover:bg-paper hover:text-ink"
            >
              <X className="size-5" />
            </button>
          </div>
        </header>

        <div className="space-y-8 px-5 py-6 sm:px-8">
          {error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : isPending ? (
            <div className="space-y-3">
              <Skeleton className="h-28 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <>
              <BriefSection account={data} />
              <ContextSection account={data} />
              <Timeline account={data} />
            </>
          )}
        </div>
      </section>
    </div>
  )
}
