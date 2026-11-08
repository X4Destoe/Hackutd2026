/** Shared API and persistence shapes; see the frozen coordination contract. */
export type UUID = string;
export type ISODateTime = string;

export type Severity = "low" | "medium" | "high" | "critical";
export type IncidentStatus =
  | "detected"
  | "triaged"
  | "awaiting_approval"
  | "assigned"
  | "in_progress"
  | "resolved"
  | "closed";

export interface Property {
  id: UUID;
  name: string;
  property_type: string;
  address_label: string;
  latitude: number;
  longitude: number;
  status: string;
  daily_disruption_cost_cents: number;
  repair_cost_cents: number;
  estimated_downtime_hours: number;
}

export interface Incident {
  id: UUID;
  property_id: UUID | null;
  assistance_request_id: UUID | null;
  kind: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  risk_score: number;
  confidence: number;
  estimated_disruption_cost_cents: number;
  required_skills: string[];
  safety_flags: string[];
  source: "sensor" | "manual" | "photon" | "simulator" | "assistance";
  detected_at: ISODateTime;
  resolved_at: ISODateTime | null;
}

export interface Observation {
  id: UUID;
  property_id: UUID;
  signal: "hvac_temperature_c" | "vibration_mm_s" | "water_intrusion" | "backup_power";
  value: number;
  unit: string;
  observed_at: ISODateTime;
  source: "synthetic" | "manual" | "external";
}

export interface Expert {
  id: UUID;
  name: string;
  specialty: string;
  qualifications: string[];
  available: boolean;
  capacity: number;
  active_assignments: number;
  assignment_cost_cents: number;
  hourly_cost_cents: number;
  service_location_label: string;
}

export type AssignmentStatus =
  | "proposed"
  | "awaiting_approval"
  | "approved"
  | "declined"
  | "in_progress"
  | "completed";

export interface Assignment {
  id: UUID;
  incident_id: UUID;
  expert_id: UUID;
  status: AssignmentStatus;
  estimated_arrival_hours: number;
  estimated_cost_cents: number;
  approved_by: string | null;
  approved_at: ISODateTime | null;
}

export interface AssistanceRequest {
  id: UUID;
  display_name: string;
  contact_channel: string;
  location_label: string;
  need_type: string;
  description: string;
  urgency: "routine" | "urgent" | "emergency";
  missing_information: string[];
  acknowledged_at: ISODateTime | null;
  last_followup_at: ISODateTime | null;
  status: "new" | "triaged" | "awaiting_expert" | "in_progress" | "resolved" | "closed";
  created_at: ISODateTime;
}

export type MessageStatus =
  | "queued"
  | "accepted"
  | "delivered"
  | "failed"
  | "received"
  | "acknowledged";

export interface ConversationMessage {
  id: UUID;
  conversation_id: string;
  incident_id: UUID | null;
  direction: "inbound" | "outbound";
  provider: "photon_beta" | "simulator";
  provider_message_id: string | null;
  body: string;
  status: MessageStatus;
  idempotency_key: string | null;
  created_at: ISODateTime;
}

export interface AuditEvent {
  id: UUID;
  entity_type: string;
  entity_id: UUID;
  event_type: string;
  actor: string;
  details: Record<string, unknown>;
  created_at: ISODateTime;
}

export interface Overview {
  property_count: number;
  active_incident_count: number;
  critical_incident_count: number;
  unassigned_case_count: number;
  available_expert_count: number;
  exposure_cents: number;
  avoidable_exposure_cents: number;
  awaiting_acknowledgment_count: number;
  severity_counts: Record<Severity, number>;
  recent_events: AuditEvent[];
}
