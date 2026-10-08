import type {
  ErrorBody,
  ErrorEnvelope,
  HealthData,
  ResponseEnvelope,
  StatusData,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly body: ErrorBody | null;

  constructor(status: number, message: string, body: ErrorBody | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export interface ApiClient {
  getHealth(): Promise<ResponseEnvelope<HealthData>>;
  getStatus(): Promise<ResponseEnvelope<StatusData>>;
}

export interface ApiClientOptions {
  baseUrl?: string;
  fetchFn?: typeof fetch;
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as ErrorBody).code === "string" &&
    typeof (error as ErrorBody).message === "string"
  );
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  const baseUrl = options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
  const fetchFn = options.fetchFn ?? ((...args: Parameters<typeof fetch>) => fetch(...args));

  async function get<T>(path: string): Promise<ResponseEnvelope<T>> {
    let response: Response;
    try {
      response = await fetchFn(`${baseUrl}${path}`, { headers: { Accept: "application/json" } });
    } catch {
      throw new ApiError(0, "The server could not be reached.");
    }
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (!response.ok) {
      if (isErrorEnvelope(payload)) {
        throw new ApiError(response.status, payload.error.message, payload.error);
      }
      throw new ApiError(response.status, `Request failed with status ${response.status}.`);
    }
    return payload as ResponseEnvelope<T>;
  }

  return {
    getHealth: () => get<HealthData>("/health"),
    getStatus: () => get<StatusData>("/status"),
  };
}
