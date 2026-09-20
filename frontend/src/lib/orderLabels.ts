import type { CustomerOrderStatus, PurchaseOrderStatus, ShipmentStatus } from "../types";

type BadgeKind = "admin" | "staff" | "danger" | "success" | "muted";

export const purchaseOrderStatusLabels: Record<PurchaseOrderStatus, string> = {
  draft: "Piszkozat",
  submitted: "Beküldve",
  partially_received: "Részben átvéve",
  received: "Átvéve",
  cancelled: "Törölve",
};

export const purchaseOrderStatusBadgeKind: Record<PurchaseOrderStatus, BadgeKind> = {
  draft: "muted",
  submitted: "admin",
  partially_received: "staff",
  received: "success",
  cancelled: "danger",
};

export const customerOrderStatusLabels: Record<CustomerOrderStatus, string> = {
  draft: "Piszkozat",
  confirmed: "Visszaigazolva",
  partially_shipped: "Részben szállítva",
  shipped: "Szállítva",
  cancelled: "Törölve",
};

export const customerOrderStatusBadgeKind: Record<CustomerOrderStatus, BadgeKind> = {
  draft: "muted",
  confirmed: "admin",
  partially_shipped: "staff",
  shipped: "success",
  cancelled: "danger",
};

export const shipmentStatusLabels: Record<ShipmentStatus, string> = {
  pending: "Függőben",
  in_transit: "Szállítás alatt",
  delivered: "Kiszállítva",
  cancelled: "Törölve",
};

export const shipmentStatusBadgeKind: Record<ShipmentStatus, BadgeKind> = {
  pending: "muted",
  in_transit: "admin",
  delivered: "success",
  cancelled: "danger",
};
