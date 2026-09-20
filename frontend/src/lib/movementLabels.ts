import type { MovementType } from "../types";

export const movementTypeLabels: Record<MovementType, string> = {
  in: "Bevételezés",
  out: "Kiadás",
  transfer: "Áthelyezés",
};

export const movementTypeBadgeKind: Record<MovementType, "success" | "danger" | "admin"> = {
  in: "success",
  out: "danger",
  transfer: "admin",
};
