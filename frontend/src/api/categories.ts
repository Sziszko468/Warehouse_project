import { apiRequest } from "./client";
import type { Category, Page } from "../types";

export interface CategoryListParams {
  include_inactive?: boolean;
  limit?: number;
  offset?: number;
}

export interface CategoryInput {
  name: string;
  description?: string | null;
}

export function listCategories(params: CategoryListParams = {}): Promise<Page<Category>> {
  return apiRequest<Page<Category>>("/categories", { query: { ...params } });
}

export function createCategory(input: CategoryInput): Promise<Category> {
  return apiRequest<Category>("/categories", { method: "POST", body: input });
}

export function updateCategory(id: number, input: Partial<CategoryInput> & { is_active?: boolean }): Promise<Category> {
  return apiRequest<Category>(`/categories/${id}`, { method: "PATCH", body: input });
}

export function deleteCategory(id: number): Promise<void> {
  return apiRequest<void>(`/categories/${id}`, { method: "DELETE" });
}
