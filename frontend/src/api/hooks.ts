import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { AccountSort, AccountView, InteractionType } from './types'

export const keys = {
  system: ['system'] as const,
  dashboard: ['dashboard'] as const,
  accounts: (view: AccountView, q: string, sort: AccountSort) => ['accounts', view, q, sort] as const,
  account: (id: string) => ['account', id] as const,
  brief: (id: string) => ['brief', id] as const,
}

export const useSystem = () => useQuery({ queryKey: keys.system, queryFn: api.system, staleTime: Infinity })
export const useDashboard = () => useQuery({ queryKey: keys.dashboard, queryFn: api.dashboard })

export const useAccounts = (view: AccountView, q: string, sort: AccountSort) =>
  useQuery({
    queryKey: keys.accounts(view, q, sort),
    queryFn: () => api.accounts({ view, q, sort }),
    placeholderData: (previous) => previous,
  })

export const useAccount = (id: string | null) =>
  useQuery({ queryKey: keys.account(id ?? ''), queryFn: () => api.account(id!), enabled: Boolean(id) })

export const useBrief = (id: string | null) =>
  useQuery({
    queryKey: keys.brief(id ?? ''),
    queryFn: () => api.brief(id!),
    enabled: Boolean(id),
    staleTime: Infinity,
  })

/** Anything that changes history invalidates every derived view: scores depend on it. */
function useInvalidateAll() {
  const client = useQueryClient()
  return () => client.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'system' })
}

export function useRegenerateBrief(id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api.brief(id, true),
    onSuccess: (brief) => client.setQueryData(keys.brief(id), brief),
  })
}

export function useCompleteFollowUp() {
  const invalidate = useInvalidateAll()
  return useMutation({
    mutationFn: ({ id, note, channel }: { id: string; note?: string; channel?: InteractionType }) =>
      api.completeFollowUp(id, { note, channel }),
    onSuccess: invalidate,
  })
}

export function useLogInteraction() {
  const invalidate = useInvalidateAll()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; type: InteractionType; notes: string; contact_id?: string | null }) =>
      api.logInteraction(id, body),
    onSuccess: invalidate,
  })
}

export function useUndoInteraction() {
  const invalidate = useInvalidateAll()
  return useMutation({ mutationFn: api.undoInteraction, onSuccess: invalidate })
}

export function useResetDemo() {
  const invalidate = useInvalidateAll()
  return useMutation({ mutationFn: api.resetDemo, onSuccess: invalidate })
}
