import type { ReactNode } from "react";

interface BadgeProps {
  kind: "admin" | "staff" | "danger" | "success" | "muted";
  children: ReactNode;
}

export function Badge({ kind, children }: BadgeProps) {
  return <span className={`badge badge--${kind}`}>{children}</span>;
}
