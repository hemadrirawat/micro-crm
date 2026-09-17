import type { ReactNode } from 'react'
import { AlertCircle, Mail } from 'lucide-react'
import type { AccountDetail } from '../../api/types'
import { INTENT_LABEL, initials, shortDate } from '../../lib/format'
import { cx } from '../../lib/styles'

function Block({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={cx('rounded-xl border border-line bg-surface p-5', className)}>
      <h3 className="mb-3 text-sm font-semibold text-ink-soft">{title}</h3>
      {children}
    </section>
  )
}

/** Structured relationship context from the rules engine: facts, blockers, why it's ranked, people. */
export function ContextSection({ account }: { account: AccountDetail }) {
  const { insight, contacts } = account
  const positive = insight.signals.filter((s) => s.points > 0)
  const negative = insight.signals.filter((s) => s.points < 0)

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Block title="Key facts">
        {insight.key_facts.length === 0 ? (
          <p className="text-sm text-ink-faint">No notable facts recorded yet.</p>
        ) : (
          <ul className="space-y-2.5">
            {insight.key_facts.map((fact) => (
              <li key={fact.evidence_id + fact.text} className="text-sm">
                <span className="mr-1.5 text-xs font-semibold text-harbor">{fact.category}</span>
                <span className="text-ink">{fact.text}</span>
                <span className="ml-1.5 text-xs text-ink-faint">{shortDate(fact.occurred_at)}</span>
              </li>
            ))}
          </ul>
        )}
        {insight.blockers.length > 0 && (
          <div className="mt-4 space-y-2 border-t border-line pt-3">
            <h4 className="text-xs font-semibold text-week">Blockers to address</h4>
            {insight.blockers.map((b) => (
              <p key={b.evidence_id + b.text} className="flex gap-2 text-sm text-ink">
                <AlertCircle className="mt-0.5 size-4 shrink-0 text-week" aria-hidden />
                {b.text}
              </p>
            ))}
          </div>
        )}
      </Block>

      <Block title="Why it’s ranked here">
        <p className="mb-3 text-sm text-ink-soft">
          {INTENT_LABEL[insight.buying_intent]}. Score {insight.priority_score}, the sum of the signals below.
        </p>
        {insight.signals.length === 0 ? (
          <p className="text-sm text-ink-faint">No signals: nothing is pending and nothing is at risk.</p>
        ) : (
          <ul className="space-y-2">
            {[...positive, ...negative].map((signal) => (
              <li key={signal.key} className="flex items-start gap-3 text-sm">
                <span
                  className={cx(
                    'w-9 shrink-0 text-right font-semibold tabular-nums',
                    signal.points < 0 ? 'text-checkin' : 'text-ink',
                  )}
                >
                  {signal.points > 0 ? `+${signal.points}` : signal.points}
                </span>
                <span className="min-w-0">
                  <span className="font-medium">{signal.label}</span>
                  <span className="block text-xs text-ink-faint">{signal.detail}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Block>

      {insight.follow_ups.length > 1 && (
        <Block title="Other open follow-ups" className="md:col-span-2">
          <ul className="space-y-1.5 text-sm">
            {insight.follow_ups.slice(1).map((f) => (
              <li key={f.title}>
                <span className="font-medium">{f.title}</span>
                <span className="text-ink-faint">. {f.detail}</span>
              </li>
            ))}
          </ul>
        </Block>
      )}

      <Block title="People" className="md:col-span-2">
        {contacts.length === 0 ? (
          <p className="text-sm text-ink-faint">No contacts on this account.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {contacts.map((c) => (
              <li key={c.id} className="flex items-center gap-3">
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-harbor-soft text-xs font-semibold text-harbor">
                  {initials(c.name)}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold">
                    {c.name}
                    {insight.suggested_action.contact_id === c.id && (
                      <span className="ml-2 text-xs font-medium text-harbor">Next contact</span>
                    )}
                  </p>
                  <p className="truncate text-xs text-ink-soft">
                    {c.role}.{' '}
                    <a href={`mailto:${c.email}`} className="inline-flex items-center gap-1 hover:text-harbor">
                      <Mail className="size-3" aria-hidden />
                      {c.email}
                    </a>
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Block>
    </div>
  )
}
