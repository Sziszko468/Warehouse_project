import { apiRequest } from "./client";
import type { User } from "../types";

export interface Token {
  access_token: string;
  token_type: string;
}

export function login(email: string, password: string): Promise<Token> {
  return apiRequest<Token>("/auth/login", { method: "POST", form: { username: email, password } });
}

export function register(email: string, password: string, full_name: string): Promise<User> {
  return apiRequest<User>("/auth/register", { method: "POST", body: { email, password, full_name } });
}

export function me(): Promise<User> {
  return apiRequest<User>("/auth/me");
}
