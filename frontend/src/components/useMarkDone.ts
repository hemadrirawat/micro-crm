import { useCompleteFollowUp, useUndoInteraction } from '../api/hooks'
import { LEVEL_LABEL } from '../lib/format'
import { useToast } from './toastContext'

/** "Mark follow-up done" with an undo toast. Shared by the queue, follow-ups list and account panel. */
export function useMarkDone() {
  const complete = useCompleteFollowUp()
  const undo = useUndoInteraction()
  const toast = useToast()

  const markDone = (id: string, name: string, note?: string) =>
    complete.mutate(
      { id, note },
      {
        onSuccess: ({ interaction, account }) =>
          toast({
            message: `Logged follow-up for ${name}. Now: ${LEVEL_LABEL[account.insight.priority_level].toLowerCase()}.`,
            actionLabel: 'Undo',
            onAction: () => undo.mutate(interaction.id),
          }),
        onError: (error) => toast({ message: `Couldn’t log the follow-up: ${error.message}` }),
      },
    )

  return { markDone, pendingId: complete.isPending ? complete.variables?.id : undefined }
}
