import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../App";
import { ApiError, type ApiClient } from "../api/client";
import type { Role } from "../api/types";

function okClient(role: Role): ApiClient {
  return {
    getHealth: async () => ({ data: { status: "ok" }, meta: { request_id: "h" } }),
    getStatus: async () => ({
      data: {
        service: "interval-assistance",
        version: "0.1.0",
        environment: "test",
        database: "ok",
        principal: { role, is_development_identity: true },
      },
      meta: { request_id: "s" },
    }),
  };
}

describe("App", () => {
  it("always shows the research-prototype notice", async () => {
    render(<App client={okClient("coach")} />);
    expect(screen.getByRole("note", { name: /research prototype/i })).toBeInTheDocument();
    await screen.findByText("System status");
  });

  it("renders status, role and development-identity warning", async () => {
    render(<App client={okClient("researcher")} />);
    expect(await screen.findByText("researcher")).toBeInTheDocument();
    expect(screen.getByText("interval-assistance 0.1.0")).toBeInTheDocument();
    expect(screen.getByText(/development identity in use/i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
  });

  it("shows an explanation and no navigation when unauthenticated", async () => {
    const client: ApiClient = {
      getHealth: async () => ({ data: { status: "ok" }, meta: { request_id: "h" } }),
      getStatus: async () => {
        throw new ApiError(401, "authentication is required");
      },
    };
    render(<App client={client} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/not authenticated/i);
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("shows unreachable when the server is down", async () => {
    const down = async () => {
      throw new ApiError(0, "The server could not be reached.");
    };
    render(<App client={{ getHealth: down, getStatus: down }} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be reached/i);
    expect(screen.getByText("unreachable")).toBeInTheDocument();
  });
});
