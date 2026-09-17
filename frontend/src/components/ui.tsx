import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { AlertTriangle, Inbox, LoaderCircle } from 'lucide-react'
import type { AccountStatus, Health, PriorityLevel } from '../api/types'
import { LEVEL_STYLES, cx } from '../lib/styles'
import { HEALTH_LABEL, LEVEL_LABEL, STATUS_LABEL } from '../lib/format'

export function PriorityPill({ level, score, onHold }: { level: PriorityLevel; score?: number; onHold?: boolean }) {
  const label = onHold ? 'On hold' : LEVEL_LABEL[level]
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold',
        LEVEL_STYLES[level].pill,
      )}
      title={score !== undefined ? `Priority score ${score}` : undefined}
    >
      <span className={cx('size-1.5 rounded-full', LEVEL_STYLES[level].bar)} aria-hidden />
      {label}
      {score !== undefined && score > 0 && <span className="font-medium opacity-70">{score}</span>}
    </span>
  )
}

export function StatusTag({ status }: { status: AccountStatus }) {
  return (
    <span
      className={cx(
        'inline-flex items-center rounded-md border px-1.5 py-px text-xs font-medium',
        status === 'prospect' ? 'border-harbor/25 text-harbor' : 'border-line-strong text-ink-soft',
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  )
}

const HEALTH_DOT: Record<Health, string> = {
  healthy: 'bg-checkin',
  watch: 'bg-week',
  at_risk: 'bg-act',
}

export function HealthIndicator({ health }: { health: Health }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-soft">
      <span className={cx('size-2 rounded-full', HEALTH_DOT[health])} aria-hidden />
      {HEALTH_LABEL[health]}
    </span>
  )
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  icon,
  children,
  className,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
  loading?: boolean
  icon?: ReactNode
}) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={cx(
        'inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold transition-colors',
        'disabled:cursor-not-allowed disabled:opacity-50',
        size === 'sm' ? 'h-8 px-2.5 text-xs' : 'h-9 px-3.5 text-sm',
        variant === 'primary' && 'bg-harbor text-white hover:bg-harbor/90',
        variant === 'secondary' && 'border border-line-strong bg-surface text-ink hover:bg-paper',
        variant === 'ghost' && 'text-ink-soft hover:bg-paper hover:text-ink',
        className,
      )}
      {...rest}
    >
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  )
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line-strong px-6 py-10 text-center">
      <Inbox className="size-6 text-ink-faint" aria-hidden />
      <p className="font-semibold">{title}</p>
      {children && <p className="max-w-sm text-sm text-ink-soft">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-act/30 bg-act-soft px-4 py-3 text-sm">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-act" aria-hidden />
      <div className="flex-1">
        <p className="font-semibold text-act">Couldn’t load this</p>
        <p className="text-ink-soft">{message}</p>
      </div>
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('animate-pulse rounded-md bg-line/70', className)} aria-hidden />
}

export function ListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="space-y-2 rounded-xl border border-line bg-surface p-4">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  )
}

export function SectionTitle({ children, aside, id }: { children: ReactNode; aside?: ReactNode; id?: string }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 id={id} className="text-base font-semibold text-ink">
        {children}
      </h2>
      {aside && <div className="text-sm text-ink-faint">{aside}</div>}
    </div>
  )
}
