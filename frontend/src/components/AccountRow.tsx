import { Check, CornerDownRight } from 'lucide-react'
import type { AccountListItem } from '../api/types'
import { TYPE_LABEL, daysAgo, shortDate } from '../lib/format'
import { Button, PriorityPill, StatusTag } from './ui'
import { LEVEL_STYLES, cx } from '../lib/styles'
import { useAccountPanel } from './useAccountPanel'
import { useMarkDone } from './useMarkDone'

interface Props {
  item: AccountListItem
  rank?: number
  compact?: boolean
}

/** One account in a queue: who, why, and what to do next. */
export function AccountRow({ item, rank, compact = false }: Props) {
  const { open } = useAccountPanel()
  const { markDone, pendingId } = useMarkDone()
  const { customer, insight, last_interaction: last } = item

  return (
    <li className="group relative flex gap-3 rounded-xl border border-line bg-surface p-4 transition-colors hover:border-line-strong sm:gap-4">
      <span
        className={cx('absolute inset-y-3 left-0 w-1 rounded-r-full', LEVEL_STYLES[insight.priority_level].bar)}
        aria-hidden
      />
      {rank !== undefined && (
        <span className="w-6 shrink-0 pt-0.5 text-right text-lg font-semibold leading-6 text-ink-faint tabular-nums">
          {rank}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
          <button
            type="button"
            onClick={() => open(customer.id)}
            className="text-left text-[15px] font-semibold leading-6 text-ink after:absolute after:inset-0 hover:text-harbor"
          >
            {customer.name}
          </button>
          <StatusTag status={customer.status} />
          <PriorityPill level={insight.priority_level} score={insight.priority_score} onHold={insight.on_hold} />
        </div>

        <p className={cx('mt-1 text-sm text-ink-soft', compact && 'line-clamp-1')}>{insight.reason}</p>

        {!compact && (
          <p className="mt-2 flex items-start gap-1.5 text-sm font-semibold text-harbor">
            <CornerDownRight className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>{insight.suggested_action.title}</span>
          </p>
        )}

        <p className="mt-2 text-xs text-ink-faint">
          {last
            ? `Last contact ${shortDate(last.occurred_at)} by ${TYPE_LABEL[last.type].toLowerCase()} (${daysAgo(
                insight.days_since_last_interaction,
              ).toLowerCase()})`
            : 'No contact recorded yet'}
        </p>
      </div>

      {insight.open_follow_up && !compact && (
        <div className="relative z-10 hidden shrink-0 self-center sm:block">
          <Button
            size="sm"
            icon={<Check className="size-3.5" aria-hidden />}
            loading={pendingId === customer.id}
            onClick={() => markDone(customer.id, customer.name)}
          >
            Mark done
          </Button>
        </div>
      )}
    </li>
  )
}
