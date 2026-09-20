import { apiRequest } from "./client";
import type { Page, Shipment, ShipmentStatus } from "../types";

export interface ShipmentListParams {
  customer_order_id?: number;
  status?: ShipmentStatus;
  limit?: number;
  offset?: number;
}

export interface ShipmentLineInput {
  customer_order_line_id: number;
  quantity: number;
}

export interface ShipmentCreateInput {
  customer_order_id: number;
  carrier?: string | null;
  tracking_number?: string | null;
  lines: ShipmentLineInput[];
}

export function listShipments(params: ShipmentListParams = {}): Promise<Page<Shipment>> {
  return apiRequest<Page<Shipment>>("/shipments", { query: { ...params } });
}

export function getShipment(id: number): Promise<Shipment> {
  return apiRequest<Shipment>(`/shipments/${id}`);
}

export function createShipment(input: ShipmentCreateInput): Promise<Shipment> {
  return apiRequest<Shipment>("/shipments", { method: "POST", body: input });
}

export function dispatchShipment(id: number): Promise<Shipment> {
  return apiRequest<Shipment>(`/shipments/${id}/dispatch`, { method: "PATCH" });
}

export function deliverShipment(id: number): Promise<Shipment> {
  return apiRequest<Shipment>(`/shipments/${id}/deliver`, { method: "PATCH" });
}

export function cancelShipment(id: number): Promise<Shipment> {
  return apiRequest<Shipment>(`/shipments/${id}/cancel`, { method: "POST" });
}
