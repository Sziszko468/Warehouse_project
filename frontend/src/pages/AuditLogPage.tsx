import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import * as auditLogsApi from "../api/auditLogs";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { t } from "../i18n/strings";
import { formatDateTime } from "../lib/format";
import type { AuditAction, AuditLog } from "../types";

const LIMIT = 25;

const ENTITY_TYPES = [
  "Category",
  "Supplier",
  "Customer",
  "Warehouse",
  "Product",
  "PurchaseOrder",
  "CustomerOrder",
  "Shipment",
];

const actionLabels: Record<AuditAction, string> = {
  create: "Létrehozva",
  update: "Módosítva",
  status_change: "Állapotváltozás",
  soft_delete: "Törölve",
};

const actionBadgeKind: Record<AuditAction, "success" | "admin" | "staff" | "danger"> = {
  create: "success",
  update: "admin",
  status_change: "staff",
  soft_delete: "danger",
};

function changesSummary(log: AuditLog): string {
  if (log.summary) return log.summary;
  if (!log.changes) return "—";
  return Object.entries(log.changes)
    .map(([field, { old, new: next }]) => `${field}: ${old} → ${next}`)
    .join(", ");
}

export function AuditLogPage() {
  const [offset, setOffset] = useState(0);
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState<AuditAction | "">("");

  const query = useQuery({
    queryKey: ["audit-logs", { offset, entityType, action }],
    queryFn: () =>
      auditLogsApi.listAuditLogs({
        offset,
        limit: LIMIT,
        entity_type: entityType || undefined,
        action: action || undefined,
      }),
  });

  const columns: Column<AuditLog>[] = [
    { key: "created", header: "Időpont", render: (row) => formatDateTime(row.created_at) },
    { key: "entity", header: "Erőforrás", render: (row) => `${row.entity_type} #${row.entity_id}` },
    {
      key: "action",
      header: "Művelet",
      render: (row) => <Badge kind={actionBadgeKind[row.action]}>{actionLabels[row.action]}</Badge>,
    },
    { key: "performer", header: "Végrehajtó", render: (row) => row.performed_by.full_name },
    { key: "details", header: "Részletek", render: (row) => changesSummary(row) },
  ];

  return (
    <>
      <PageHeader title="Audit napló" subtitle="Minden létrehozás, módosítás, állapotváltozás és törlés nyomon követése." />
      <div className="page-content">
        <Panel>
          <div className="filters-bar">
            <Field label="Erőforrás típusa" htmlFor="audit-entity-type">
              <select
                id="audit-entity-type"
                value={entityType}
                onChange={(event) => {
                  setEntityType(event.target.value);
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {ENTITY_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Művelet" htmlFor="audit-action">
              <select
                id="audit-action"
                value={action}
                onChange={(event) => {
                  setAction(event.target.value as AuditAction | "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {(Object.keys(actionLabels) as AuditAction[]).map((key) => (
                  <option key={key} value={key}>
                    {actionLabels[key]}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <DataTable
            columns={columns}
            rows={query.data?.items ?? []}
            rowKey={(row) => row.id}
            isLoading={query.isLoading}
            emptyMessage={t.noResults}
          />
          {query.data && <Pagination total={query.data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
        </Panel>
      </div>
    </>
  );
}
