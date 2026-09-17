// Mirrors the FastAPI response models in backend/app/schemas.py.

export type AccountStatus = 'prospect' | 'customer'
export type InteractionType = 'email' | 'call' | 'meeting' | 'note'
export type PriorityLevel = 'act_now' | 'this_week' | 'check_in' | 'monitor'
export type Health = 'healthy' | 'watch' | 'at_risk'
export type Intent = 'high' | 'medium' | 'low' | 'unknown' | 'existing_customer'
export type AccountView = 'all' | 'prospects' | 'customers' | 'needs_attention'
export type AccountSort = 'priority' | 'last_interaction' | 'status' | 'name'

export interface Customer {
  id: string
  name: string
  status: AccountStatus
  created_at: string
}

export interface Contact {
  id: string
  customer_id: string
  name: string
  email: string
  role: string
}

export interface Interaction {
  id: string
  customer_id: string
  contact_id: string | null
  type: InteractionType
  occurred_at: string
  notes: string
  source: 'seed' | 'user'
}

export interface TimelineEntry extends Interaction {
  contact_name: string | null
  contact_role: string | null
}

export interface Signal {
  key: string
  label: string
  points: number
  detail: string
  evidence_ids: string[]
}

export interface Fact {
  category: string
  text: string
  evidence_id: string
  occurred_at: string
}

export interface FollowUp {
  title: string
  detail: string
  signal_key: string
  evidence_ids: string[]
}

export interface SuggestedAction {
  title: string
  signal_key: string | null
  contact_id: string | null
  contact_name: string | null
}

export interface AccountInsight {
  customer_id: string
  last_interaction_at: string | null
  days_since_last_interaction: number | null
  last_interaction_id: string | null
  interaction_count: number
  priority_score: number
  priority_level: PriorityLevel
  on_hold: boolean
  open_follow_up: boolean
  follow_ups: FollowUp[]
  buying_intent: Intent
  urgency: 'high' | 'medium' | 'low'
  relationship_health: Health
  reason: string
  suggested_action: SuggestedAction
  signals: Signal[]
  blockers: { text: string; evidence_id: string }[]
  key_facts: Fact[]
  summary: string
}

export interface LastInteraction {
  id: string
  type: InteractionType
  occurred_at: string
  notes: string
  contact_name: string | null
}

export interface AccountListItem {
  customer: Customer
  primary_contact: Contact | null
  last_interaction: LastInteraction | null
  insight: AccountInsight
}

export interface AccountDetail {
  customer: Customer
  contacts: Contact[]
  insight: AccountInsight
  timeline: TimelineEntry[]
}

export interface Dashboard {
  today: string
  level_counts: Record<PriorityLevel, number>
  health: Record<Health, number>
  prospects: number
  customers: number
  needs_attention: AccountListItem[]
  opportunities: AccountListItem[]
  on_hold: AccountListItem[]
  recent_activity: { interaction: TimelineEntry; customer_id: string; customer_name: string }[]
}

export interface Evidence {
  interaction_id: string
  occurred_at: string
  type: InteractionType
  quote: string
}

export interface AccountBrief {
  customer_id: string
  summary: string
  key_facts: string[]
  intent: Intent
  urgency: 'high' | 'medium' | 'low'
  blockers: string[]
  next_action: string
  reason: string
  evidence: Evidence[]
  recipient: { contact_id: string; name: string; email: string; role: string } | null
  message_subject: string
  suggested_message: string
  talking_points: string[]
  insufficient_information: boolean
  source: 'llm' | 'rules'
  model: string | null
  fallback_reason: string | null
  generated_at: string
}

export interface SystemInfo {
  status: 'ok'
  ai_mode: 'llm' | 'rules'
  model: string | null
  today: string
}

export interface InteractionResult {
  interaction: Interaction
  account: AccountListItem
}
