// Hand-written mirror of the Phase 1 backend schemas (interval_assistance.schemas).
// A generated client is a later decision; backend tests pin the exposed paths.

export type Role = "coach" | "athlete" | "researcher";

export interface ResponseEnvelope<T> {
  data: T;
  meta: { request_id: string };
}

export interface ErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string | null;
}

export interface ErrorEnvelope {
  error: ErrorBody;
}

export type ComponentState = "ok" | "unavailable";

export interface HealthData {
  status: ComponentState;
}

export interface StatusData {
  service: string;
  version: string;
  environment: string;
  database: ComponentState;
  principal: { role: Role; is_development_identity: boolean };
}
