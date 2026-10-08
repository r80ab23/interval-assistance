import { describe, expect, it } from "vitest";

import { ApiError, createApiClient } from "../api/client";

function fakeFetch(status: number, body: unknown): typeof fetch {
  return (async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    })) as typeof fetch;
}

describe("api client", () => {
  it("returns typed envelopes on success", async () => {
    const body = { data: { status: "ok" }, meta: { request_id: "r1" } };
    const client = createApiClient({ baseUrl: "/api/v1", fetchFn: fakeFetch(200, body) });
    expect((await client.getHealth()).data.status).toBe("ok");
  });

  it("requests the versioned path", async () => {
    const seen: string[] = [];
    const fetchFn = (async (url: string) => {
      seen.push(url);
      return new Response("{}", { status: 200 });
    }) as unknown as typeof fetch;
    await createApiClient({ baseUrl: "/api/v1", fetchFn }).getStatus();
    expect(seen).toEqual(["/api/v1/status"]);
  });

  it("maps error envelopes to ApiError", async () => {
    const error = { code: "authentication_required", message: "no", details: {}, request_id: "r" };
    const client = createApiClient({ fetchFn: fakeFetch(401, { error }) });
    await expect(client.getStatus()).rejects.toMatchObject({ status: 401, body: error });
  });

  it("handles non-envelope failures", async () => {
    const client = createApiClient({ fetchFn: fakeFetch(500, "oops") });
    const err = await client.getStatus().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(500);
    expect((err as ApiError).body).toBeNull();
  });

  it("reports network failure as status 0", async () => {
    const fetchFn = (async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    await expect(createApiClient({ fetchFn }).getHealth()).rejects.toMatchObject({ status: 0 });
  });
});
