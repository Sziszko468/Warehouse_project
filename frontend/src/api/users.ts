import { apiRequest } from "./client";
import type { Page, User, UserRole } from "../types";

export interface UserListParams {
  role?: UserRole;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}

export function listUsers(params: UserListParams = {}): Promise<Page<User>> {
  return apiRequest<Page<User>>("/users", { query: params });
}

export interface UserUpdateInput {
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
}

export function updateUser(id: number, input: UserUpdateInput): Promise<User> {
  return apiRequest<User>(`/users/${id}`, { method: "PATCH", body: input });
}
