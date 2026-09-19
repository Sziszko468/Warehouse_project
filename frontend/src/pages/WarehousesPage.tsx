import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { EditIcon, PlusIcon, TrashIcon } from "../components/ui/icons";
import { Modal } from "../components/ui/Modal";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { t } from "../i18n/strings";
import { getErrorMessage } from "../lib/errors";
import type { Warehouse } from "../types";

const LIMIT = 20;

export function WarehousesPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [editing, setEditing] = useState<Warehouse | "new" | null>(null);
  const [deleting, setDeleting] = useState<Warehouse | null>(null);

  const query = useQuery({
    queryKey: ["warehouses", { offset, includeInactive }],
    queryFn: () => warehousesApi.listWarehouses({ offset, limit: LIMIT, include_inactive: includeInactive }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["warehouses"] });
  }

  const columns: Column<Warehouse>[] = [
    { key: "name", header: t.name, render: (row) => row.name },
    { key: "address", header: "Cím", render: (row) => row.address || <span className="text-faint">—</span> },
    {
      key: "status",
      header: "Állapot",
      render: (row) => (row.is_active ? <Badge kind="success">{t.active}</Badge> : <Badge kind="muted">{t.inactive}</Badge>),
    },
  ];

  if (isAdmin) {
    columns.push({
      key: "actions",
      header: t.actions,
      render: (row) => (
        <div className="row-actions">
          <Button variant="ghost" size="sm" className="btn--icon" onClick={() => setEditing(row)} aria-label={t.edit}>
            <EditIcon />
          </Button>
          {row.is_active && (
            <Button variant="ghost" size="sm" className="btn--icon" onClick={() => setDeleting(row)} aria-label={t.delete}>
              <TrashIcon />
            </Button>
          )}
        </div>
      ),
    });
  }

  return (
    <>
      <PageHeader
        title="Raktárak"
        subtitle="A készlet fizikai tárolási helyei."
        actions={
          isAdmin && (
            <Button onClick={() => setEditing("new")}>
              <PlusIcon />
              {t.create}
            </Button>
          )
        }
      />
      <div className="page-content">
        <Panel>
          <div className="filters-bar">
            <div className="checkbox-field">
              <input
                id="includeInactive"
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => {
                  setIncludeInactive(event.target.checked);
                  setOffset(0);
                }}
              />
              <label htmlFor="includeInactive">{t.showInactive}</label>
            </div>
          </div>
          <DataTable columns={columns} rows={query.data?.items ?? []} rowKey={(row) => row.id} isLoading={query.isLoading} />
          {query.data && <Pagination total={query.data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
        </Panel>
      </div>

      {editing && (
        <WarehouseFormModal
          warehouse={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            invalidate();
            setEditing(null);
            showSuccess("Raktár mentve.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title={t.confirmDeleteTitle}
          message={`Biztosan törli a(z) „${deleting.name}” raktárt?`}
          isDangerous
          onCancel={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await warehousesApi.deleteWarehouse(deleting.id);
              invalidate();
              showSuccess("Raktár törölve.");
            } catch (err) {
              showError(getErrorMessage(err));
            } finally {
              setDeleting(null);
            }
          }}
        />
      )}
    </>
  );
}

interface WarehouseFormModalProps {
  warehouse: Warehouse | null;
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

function WarehouseFormModal({ warehouse, onClose, onSaved, onError }: WarehouseFormModalProps) {
  const [name, setName] = useState(warehouse?.name ?? "");
  const [address, setAddress] = useState(warehouse?.address ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      if (warehouse) {
        await warehousesApi.updateWarehouse(warehouse.id, { name, address: address || null });
      } else {
        await warehousesApi.createWarehouse({ name, address: address || null });
      }
      onSaved();
    } catch (err) {
      onError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title={warehouse ? "Raktár szerkesztése" : "Új raktár"} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <Field label={t.name} htmlFor="wh-name" required>
          <input id="wh-name" value={name} onChange={(event) => setName(event.target.value)} required autoFocus />
        </Field>
        <Field label="Cím" htmlFor="wh-address">
          <textarea id="wh-address" value={address ?? ""} onChange={(event) => setAddress(event.target.value)} />
        </Field>
        <div className="form-actions">
          <Button variant="ghost" onClick={onClose}>
            {t.cancel}
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {t.save}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
