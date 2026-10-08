import { describe, expect, it } from "vitest";

import { navigationFor } from "../navigation";

describe("navigationFor", () => {
  it.each(["coach", "athlete", "researcher"] as const)("shows status to %s", (role) => {
    expect(navigationFor(role).map((e) => e.id)).toEqual(["status"]);
  });

  it("denies by default without a role", () => {
    expect(navigationFor(null)).toEqual([]);
  });
});
