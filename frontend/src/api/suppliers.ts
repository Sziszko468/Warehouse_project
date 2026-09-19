import { apiRequest } from "./client";
import type { Page, Supplier } from "../types";

export interface SupplierListParams {
  include_inactive?: boolean;
  limit?: number;
  offset?: number;
}

export interface SupplierInput {
  name: string;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}

export function listSuppliers(params: SupplierListParams = {}): Promise<Page<Supplier>> {
  return apiRequest<Page<Supplier>>("/suppliers", { query: params });
}

export function createSupplier(input: SupplierInput): Promise<Supplier> {
  return apiRequest<Supplier>("/suppliers", { method: "POST", body: input });
}

export function updateSupplier(id: number, input: Partial<SupplierInput> & { is_active?: boolean }): Promise<Supplier> {
  return apiRequest<Supplier>(`/suppliers/${id}`, { method: "PATCH", body: input });
}

export function deleteSupplier(id: number): Promise<void> {
  return apiRequest<void>(`/suppliers/${id}`, { method: "DELETE" });
}
