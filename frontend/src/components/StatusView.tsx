import type { ApiError } from "../api/client";
import type { HealthData, ResponseEnvelope, StatusData } from "../api/types";

export interface StatusState {
  loading: boolean;
  health: ResponseEnvelope<HealthData> | null;
  status: ResponseEnvelope<StatusData> | null;
  error: ApiError | null;
}

function describeError(error: ApiError): string {
  if (error.status === 401) {
    return "Not authenticated. Phase 1 has no login; enable the backend development identity.";
  }
  if (error.status === 403) return "This role is not permitted to view the status.";
  return error.message;
}

export function StatusView({ state }: { state: StatusState }) {
  if (state.loading) return <p>Loading status...</p>;
  const { health, status, error } = state;
  return (
    <section aria-labelledby="status-heading">
      <h2 id="status-heading">System status</h2>
      <dl>
        <dt>Service health</dt>
        <dd>{health ? health.data.status : "unreachable"}</dd>
        {status && (
          <>
            <dt>Service</dt>
            <dd>
              {status.data.service} {status.data.version}
            </dd>
            <dt>Environment</dt>
            <dd>{status.data.environment}</dd>
            <dt>Database</dt>
            <dd>{status.data.database}</dd>
            <dt>Role</dt>
            <dd>{status.data.principal.role}</dd>
          </>
        )}
      </dl>
      {status?.data.principal.is_development_identity && (
        <p role="status" className="dev-identity">
          Development identity in use. This is not an authenticated user.
        </p>
      )}
      {error && <p role="alert">{describeError(error)}</p>}
    </section>
  );
}
