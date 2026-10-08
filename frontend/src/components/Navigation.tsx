import type { Role } from "../api/types";
import { navigationFor, type ViewId } from "../navigation";

interface Props {
  role: Role | null;
  current: ViewId;
  onSelect: (view: ViewId) => void;
}

export function Navigation({ role, current, onSelect }: Props) {
  const entries = navigationFor(role);
  if (entries.length === 0) return null;
  return (
    <nav aria-label="Main">
      <ul>
        {entries.map((entry) => (
          <li key={entry.id}>
            <button
              type="button"
              aria-current={entry.id === current ? "page" : undefined}
              onClick={() => onSelect(entry.id)}
            >
              {entry.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
