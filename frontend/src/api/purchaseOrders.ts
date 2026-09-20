import { apiRequest, downloadFile } from "./client";
import type { Page, PurchaseOrder, PurchaseOrderStatus } from "../types";

export interface PurchaseOrderListParams {
  status?: PurchaseOrderStatus;
  supplier_id?: number;
  warehouse_id?: number;
  limit?: number;
  offset?: number;
}

export interface PurchaseOrderLineInput {
  product_id: number;
  quantity_ordered: number;
  unit_price: string;
}

export interface PurchaseOrderCreateInput {
  supplier_id: number;
  warehouse_id: number;
  notes?: string | null;
  lines: PurchaseOrderLineInput[];
}

export interface PurchaseOrderReceiveLineInput {
  purchase_order_line_id: number;
  quantity: number;
}

export function listPurchaseOrders(params: PurchaseOrderListParams = {}): Promise<Page<PurchaseOrder>> {
  return apiRequest<Page<PurchaseOrder>>("/purchase-orders", { query: { ...params } });
}

export function exportPurchaseOrders(params: PurchaseOrderListParams = {}): Promise<void> {
  return downloadFile("/purchase-orders/export", { ...params });
}

export function getPurchaseOrder(id: number): Promise<PurchaseOrder> {
  return apiRequest<PurchaseOrder>(`/purchase-orders/${id}`);
}

export function createPurchaseOrder(input: PurchaseOrderCreateInput): Promise<PurchaseOrder> {
  return apiRequest<PurchaseOrder>("/purchase-orders", { method: "POST", body: input });
}

export function submitPurchaseOrder(id: number): Promise<PurchaseOrder> {
  return apiRequest<PurchaseOrder>(`/purchase-orders/${id}/submit`, { method: "POST" });
}

export function cancelPurchaseOrder(id: number): Promise<PurchaseOrder> {
  return apiRequest<PurchaseOrder>(`/purchase-orders/${id}/cancel`, { method: "POST" });
}

export function receivePurchaseOrder(
  id: number,
  lines: PurchaseOrderReceiveLineInput[],
  note?: string | null,
): Promise<PurchaseOrder> {
  return apiRequest<PurchaseOrder>(`/purchase-orders/${id}/receive`, { method: "POST", body: { lines, note: note ?? null } });
}
