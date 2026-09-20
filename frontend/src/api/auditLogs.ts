import { apiRequest } from "./client";
import type { AuditAction, AuditLog, Page } from "../types";

export interface AuditLogListParams {
  entity_type?: string;
  entity_id?: number;
  action?: AuditAction;
  performed_by_id?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export function listAuditLogs(params: AuditLogListParams = {}): Promise<Page<AuditLog>> {
  return apiRequest<Page<AuditLog>>("/audit-logs", { query: { ...params } });
}
