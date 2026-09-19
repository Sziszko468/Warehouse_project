import { apiRequest } from "./client";
import type { Page, Warehouse } from "../types";

export interface WarehouseListParams {
  include_inactive?: boolean;
  limit?: number;
  offset?: number;
}

export interface WarehouseInput {
  name: string;
  address?: string | null;
}

export function listWarehouses(params: WarehouseListParams = {}): Promise<Page<Warehouse>> {
  return apiRequest<Page<Warehouse>>("/warehouses", { query: params });
}

export function createWarehouse(input: WarehouseInput): Promise<Warehouse> {
  return apiRequest<Warehouse>("/warehouses", { method: "POST", body: input });
}

export function updateWarehouse(id: number, input: Partial<WarehouseInput> & { is_active?: boolean }): Promise<Warehouse> {
  return apiRequest<Warehouse>(`/warehouses/${id}`, { method: "PATCH", body: input });
}

export function deleteWarehouse(id: number): Promise<void> {
  return apiRequest<void>(`/warehouses/${id}`, { method: "DELETE" });
}
