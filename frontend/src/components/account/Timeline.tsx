import { useState, type FormEvent } from 'react'
import { CalendarDays, Mail, NotebookPen, Phone, Undo2 } from 'lucide-react'
import { useLogInteraction, useUndoInteraction } from '../../api/hooks'
import type { AccountDetail, InteractionType } from '../../api/types'
import { TYPE_LABEL, shortDate } from '../../lib/format'
import { useToast } from '../toastContext'
import { Button } from '../ui'
import { cx } from '../../lib/styles'

const TYPE_ICON = { email: Mail, call: Phone, meeting: CalendarDays, note: NotebookPen } as const

export function Timeline({ account }: { account: AccountDetail }) {
  const undo = useUndoInteraction()
  const evidence = new Set(account.insight.signals.flatMap((s) => s.evidence_ids))

  return (
    <section aria-labelledby="timeline-title">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 id="timeline-title" className="text-base font-semibold">
          Interaction timeline
        </h3>
        <span className="text-sm text-ink-faint">{account.timeline.length} interactions</span>
      </div>

      <LogInteractionForm account={account} />

      {account.timeline.length === 0 ? (
        <p className="mt-4 text-sm text-ink-faint">No interactions yet. Log the first one above.</p>
      ) : (
        <ol className="relative mt-5 space-y-5 border-l border-line pl-6">
          {account.timeline.map((entry) => {
            const Icon = TYPE_ICON[entry.type]
            return (
              <li key={entry.id} className="relative">
                <span
                  className={cx(
                    'absolute -left-[37px] grid size-6 place-items-center rounded-full border bg-surface',
                    evidence.has(entry.id) ? 'border-harbor text-harbor' : 'border-line-strong text-ink-faint',
                  )}
                  aria-hidden
                >
                  <Icon className="size-3" />
                </span>
                <p className="text-xs text-ink-faint">
                  <span className="font-semibold text-ink-soft">{shortDate(entry.occurred_at)}</span>
                  {', '}
                  {TYPE_LABEL[entry.type].toLowerCase()}
                  {entry.contact_name && ` with ${entry.contact_name}`}
                  {entry.type === 'note' && ' (internal)'}
                  {evidence.has(entry.id) && <span className="ml-2 text-harbor">Used in ranking</span>}
                </p>
                <p className="mt-0.5 text-sm leading-relaxed text-ink">{entry.notes}</p>
                {entry.source === 'user' && (
                  <button
                    type="button"
                    className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-ink-soft hover:text-ink"
                    onClick={() => undo.mutate(entry.id)}
                    disabled={undo.isPending}
                  >
                    <Undo2 className="size-3" aria-hidden />
                    Remove
                  </button>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}

function LogInteractionForm({ account }: { account: AccountDetail }) {
  const log = useLogInteraction()
  const toast = useToast()
  const [type, setType] = useState<InteractionType>('call')
  const [contactId, setContactId] = useState(account.insight.suggested_action.contact_id ?? account.contacts[0]?.id ?? '')
  const [notes, setNotes] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    log.mutate(
      { id: account.customer.id, type, notes, contact_id: contactId || null },
      {
        onSuccess: ({ account: updated }) => {
          setNotes('')
          toast({ message: `Logged. ${updated.insight.suggested_action.title}.` })
        },
      },
    )
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-line bg-surface p-3">
      <label htmlFor="log-notes" className="sr-only">
        What happened?
      </label>
      <textarea
        id="log-notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={2}
        placeholder="Log what happened, e.g. “Sarah said partners approved and asked for a kickoff call.”"
        className="w-full resize-y rounded-md border-0 bg-transparent p-1 text-sm placeholder:text-ink-faint focus:outline-none"
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <select
          aria-label="Interaction type"
          value={type}
          onChange={(e) => setType(e.target.value as InteractionType)}
          className="h-8 rounded-md border border-line-strong bg-surface px-2 text-xs"
        >
          {(Object.keys(TYPE_LABEL) as InteractionType[]).map((t) => (
            <option key={t} value={t}>
              {TYPE_LABEL[t]}
            </option>
          ))}
        </select>
        {account.contacts.length > 0 && (
          <select
            aria-label="Contact"
            value={contactId}
            onChange={(e) => setContactId(e.target.value)}
            className="h-8 rounded-md border border-line-strong bg-surface px-2 text-xs"
          >
            {account.contacts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
        {log.error && <span className="text-xs text-act">{log.error.message}</span>}
        <Button type="submit" size="sm" variant="primary" className="ml-auto" disabled={notes.trim().length < 3} loading={log.isPending}>
          Log interaction
        </Button>
      </div>
    </form>
  )
}
