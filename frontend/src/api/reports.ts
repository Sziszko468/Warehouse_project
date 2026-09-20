import { apiRequest } from "./client";
import type { CategoryBrief, CustomerBrief, SupplierBrief, WarehouseBrief } from "../types";

export interface StockValuationByWarehouse {
  warehouse: WarehouseBrief;
  total_quantity: number;
  total_value: string;
}

export interface StockValuationByCategory {
  category: CategoryBrief;
  total_quantity: number;
  total_value: string;
}

export interface StockValuationReport {
  total_quantity: number;
  total_value: string;
  by_warehouse: StockValuationByWarehouse[];
  by_category: StockValuationByCategory[];
}

export interface PurchaseActivityRow {
  supplier: SupplierBrief;
  orders_submitted: number;
  orders_received: number;
  received_value: string;
}

export interface SalesFulfillmentActivityRow {
  customer: CustomerBrief;
  orders_confirmed: number;
  shipments_created: number;
  shipped_value: string;
}

export interface StockValuationParams {
  warehouse_id?: number;
  category_id?: number;
}

export interface ActivityDateRangeParams {
  date_from?: string;
  date_to?: string;
}

export function getStockValuation(params: StockValuationParams = {}): Promise<StockValuationReport> {
  return apiRequest<StockValuationReport>("/reports/stock-valuation", { query: { ...params } });
}

export function getPurchaseActivity(params: ActivityDateRangeParams = {}): Promise<PurchaseActivityRow[]> {
  return apiRequest<PurchaseActivityRow[]>("/reports/purchase-activity", { query: { ...params } });
}

export function getSalesFulfillmentActivity(
  params: ActivityDateRangeParams = {},
): Promise<SalesFulfillmentActivityRow[]> {
  return apiRequest<SalesFulfillmentActivityRow[]>("/reports/sales-fulfillment-activity", { query: { ...params } });
}
