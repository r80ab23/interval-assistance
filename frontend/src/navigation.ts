import type { Role } from "./api/types";

export type ViewId = "status";

export interface NavigationEntry {
  id: ViewId;
  label: string;
  roles: readonly Role[];
}

// Visibility only. Authorization is enforced by the backend, never by the UI.
// Later phases add entries here.
export const NAVIGATION: readonly NavigationEntry[] = [
  { id: "status", label: "Status", roles: ["coach", "athlete", "researcher"] },
];

// Default deny: an unknown or missing role sees no navigation.
export function navigationFor(role: Role | null): NavigationEntry[] {
  if (role === null) return [];
  return NAVIGATION.filter((entry) => entry.roles.includes(role));
}
