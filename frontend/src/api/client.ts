import type {
  AccountBrief,
  AccountDetail,
  AccountListItem,
  AccountSort,
  AccountView,
  Dashboard,
  InteractionResult,
  InteractionType,
  SystemInfo,
} from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'Can’t reach the API. Is the backend running on port 8000?')
  }
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response))
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg
  } catch {
    // fall through to the generic message
  }
  // The Vite dev proxy answers 502/504 when nothing is listening on the API port,
  // so the useful message is "start the backend", not the status code.
  if (response.status === 502 || response.status === 503 || response.status === 504) {
    return 'Can’t reach the API. Is the backend running on port 8000?'
  }
  return `Request failed (${response.status})`
}

export const api = {
  system: () => request<SystemInfo>('/system'),
  dashboard: () => request<Dashboard>('/dashboard'),
  accounts: (params: { view: AccountView; q: string; sort: AccountSort }) =>
    request<AccountListItem[]>(`/accounts?${new URLSearchParams(params)}`),
  account: (id: string) => request<AccountDetail>(`/accounts/${encodeURIComponent(id)}`),
  brief: (id: string, refresh = false) =>
    request<AccountBrief>(`/accounts/${encodeURIComponent(id)}/brief?refresh=${refresh}`, { method: 'POST' }),
  completeFollowUp: (id: string, body: { note?: string; channel?: InteractionType }) =>
    request<InteractionResult>(`/accounts/${encodeURIComponent(id)}/follow-ups/complete`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  logInteraction: (id: string, body: { type: InteractionType; notes: string; contact_id?: string | null }) =>
    request<InteractionResult>(`/accounts/${encodeURIComponent(id)}/interactions`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  undoInteraction: (interactionId: string) =>
    request<AccountListItem>(`/interactions/${encodeURIComponent(interactionId)}`, { method: 'DELETE' }),
  resetDemo: () => request<void>('/demo/reset', { method: 'POST' }),
}
