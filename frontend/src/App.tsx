import { useEffect, useState } from "react";

import { ApiError, createApiClient, type ApiClient } from "./api/client";
import { Navigation } from "./components/Navigation";
import { ResearchNotice } from "./components/ResearchNotice";
import { StatusView, type StatusState } from "./components/StatusView";
import type { ViewId } from "./navigation";

const defaultClient = createApiClient();

function toApiError(reason: unknown): ApiError | null {
  if (reason === null || reason === undefined) return null;
  return reason instanceof ApiError ? reason : new ApiError(0, String(reason));
}

export function App({ client = defaultClient }: { client?: ApiClient }) {
  const [view, setView] = useState<ViewId>("status");
  const [state, setState] = useState<StatusState>({
    loading: true,
    health: null,
    status: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([client.getHealth(), client.getStatus()]).then(([health, status]) => {
      if (cancelled) return;
      const failure = [health, status].find((r) => r.status === "rejected");
      setState({
        loading: false,
        health: health.status === "fulfilled" ? health.value : null,
        status: status.status === "fulfilled" ? status.value : null,
        error: toApiError(failure && failure.status === "rejected" ? failure.reason : null),
      });
    });
    return () => {
      cancelled = true;
    };
  }, [client]);

  const role = state.status?.data.principal.role ?? null;

  return (
    <main>
      <h1>Interval Assistance</h1>
      <ResearchNotice />
      <Navigation role={role} current={view} onSelect={setView} />
      {view === "status" && <StatusView state={state} />}
    </main>
  );
}
