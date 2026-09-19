import { ApiError } from "../api/client";

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof Error) return error.message;
  return "Váratlan hiba történt.";
}
