import { apiRequest } from "./client";
import type { Page, Product } from "../types";

export interface ProductListParams {
  include_inactive?: boolean;
  category_id?: number;
  supplier_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface ProductInput {
  sku: string;
  name: string;
  description?: string | null;
  category_id: number;
  supplier_id?: number | null;
  unit_price: string;
  min_stock_threshold: number;
}

export function listProducts(params: ProductListParams = {}): Promise<Page<Product>> {
  return apiRequest<Page<Product>>("/products", { query: { ...params } });
}

export function createProduct(input: ProductInput): Promise<Product> {
  return apiRequest<Product>("/products", { method: "POST", body: input });
}

export function updateProduct(id: number, input: Partial<ProductInput> & { is_active?: boolean }): Promise<Product> {
  return apiRequest<Product>(`/products/${id}`, { method: "PATCH", body: input });
}

export function deleteProduct(id: number): Promise<void> {
  return apiRequest<void>(`/products/${id}`, { method: "DELETE" });
}
