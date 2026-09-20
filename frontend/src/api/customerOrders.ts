import { apiRequest, downloadFile } from "./client";
import type { CustomerOrder, CustomerOrderStatus, Page } from "../types";

export interface CustomerOrderListParams {
  status?: CustomerOrderStatus;
  customer_id?: number;
  warehouse_id?: number;
  limit?: number;
  offset?: number;
}

export interface CustomerOrderLineInput {
  product_id: number;
  quantity_ordered: number;
}

export interface CustomerOrderCreateInput {
  customer_id: number;
  warehouse_id: number;
  notes?: string | null;
  lines: CustomerOrderLineInput[];
}

export function listCustomerOrders(params: CustomerOrderListParams = {}): Promise<Page<CustomerOrder>> {
  return apiRequest<Page<CustomerOrder>>("/customer-orders", { query: { ...params } });
}

export function exportCustomerOrders(params: CustomerOrderListParams = {}): Promise<void> {
  return downloadFile("/customer-orders/export", { ...params });
}

export function getCustomerOrder(id: number): Promise<CustomerOrder> {
  return apiRequest<CustomerOrder>(`/customer-orders/${id}`);
}

export function createCustomerOrder(input: CustomerOrderCreateInput): Promise<CustomerOrder> {
  return apiRequest<CustomerOrder>("/customer-orders", { method: "POST", body: input });
}

export function confirmCustomerOrder(id: number): Promise<CustomerOrder> {
  return apiRequest<CustomerOrder>(`/customer-orders/${id}/confirm`, { method: "POST" });
}

export function cancelCustomerOrder(id: number): Promise<CustomerOrder> {
  return apiRequest<CustomerOrder>(`/customer-orders/${id}/cancel`, { method: "POST" });
}
