import { apiRequest, downloadFile } from "./client";
import type { LowStock, MovementType, Page, Stock, StockMovement } from "../types";

export interface StockListParams {
  product_id?: number;
  warehouse_id?: number;
  limit?: number;
  offset?: number;
}

export function listStock(params: StockListParams = {}): Promise<Page<Stock>> {
  return apiRequest<Page<Stock>>("/stock", { query: { ...params } });
}

export function exportStock(params: StockListParams = {}): Promise<void> {
  return downloadFile("/stock/export", { ...params });
}

export interface LowStockListParams {
  warehouse_id?: number;
  limit?: number;
  offset?: number;
}

export function listLowStock(params: LowStockListParams = {}): Promise<Page<LowStock>> {
  return apiRequest<Page<LowStock>>("/stock/low-stock", { query: { ...params } });
}

export interface MovementListParams {
  product_id?: number;
  warehouse_id?: number;
  movement_type?: MovementType;
  performed_by_id?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export function listMovements(params: MovementListParams = {}): Promise<Page<StockMovement>> {
  return apiRequest<Page<StockMovement>>("/stock/movements", { query: { ...params } });
}

export function exportMovements(params: MovementListParams = {}): Promise<void> {
  return downloadFile("/stock/movements/export", { ...params });
}

export interface StockInInput {
  product_id: number;
  warehouse_id: number;
  quantity: number;
  note?: string | null;
}

export function stockIn(input: StockInInput): Promise<StockMovement> {
  return apiRequest<StockMovement>("/stock/in", { method: "POST", body: input });
}

export interface StockOutInput {
  product_id: number;
  warehouse_id: number;
  quantity: number;
  note?: string | null;
}

export function stockOut(input: StockOutInput): Promise<StockMovement> {
  return apiRequest<StockMovement>("/stock/out", { method: "POST", body: input });
}

export interface StockTransferInput {
  product_id: number;
  from_warehouse_id: number;
  to_warehouse_id: number;
  quantity: number;
  note?: string | null;
}

export function stockTransfer(input: StockTransferInput): Promise<StockMovement> {
  return apiRequest<StockMovement>("/stock/transfer", { method: "POST", body: input });
}
