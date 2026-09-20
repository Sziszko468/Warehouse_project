import { apiRequest } from "./client";
import type { Customer, Page } from "../types";

export interface CustomerListParams {
  include_inactive?: boolean;
  limit?: number;
  offset?: number;
}

export interface CustomerInput {
  name: string;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}

export function listCustomers(params: CustomerListParams = {}): Promise<Page<Customer>> {
  return apiRequest<Page<Customer>>("/customers", { query: { ...params } });
}

export function createCustomer(input: CustomerInput): Promise<Customer> {
  return apiRequest<Customer>("/customers", { method: "POST", body: input });
}

export function updateCustomer(id: number, input: Partial<CustomerInput> & { is_active?: boolean }): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${id}`, { method: "PATCH", body: input });
}

export function deleteCustomer(id: number): Promise<void> {
  return apiRequest<void>(`/customers/${id}`, { method: "DELETE" });
}
