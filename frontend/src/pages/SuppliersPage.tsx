import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as suppliersApi from "../api/suppliers";
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
import type { Supplier } from "../types";

const LIMIT = 20;

export function SuppliersPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [editing, setEditing] = useState<Supplier | "new" | null>(null);
  const [deleting, setDeleting] = useState<Supplier | null>(null);

  const query = useQuery({
    queryKey: ["suppliers", { offset, includeInactive }],
    queryFn: () => suppliersApi.listSuppliers({ offset, limit: LIMIT, include_inactive: includeInactive }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["suppliers"] });
  }

  const columns: Column<Supplier>[] = [
    { key: "name", header: t.name, render: (row) => row.name },
    { key: "contact", header: "Kapcsolattartó", render: (row) => row.contact_name || <span className="text-faint">—</span> },
    { key: "email", header: "E-mail", render: (row) => row.email || <span className="text-faint">—</span> },
    { key: "phone", header: "Telefon", render: (row) => row.phone || <span className="text-faint">—</span> },
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
        title="Beszállítók"
        subtitle="Termékeket szállító partnerek."
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
        <SupplierFormModal
          supplier={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            invalidate();
            setEditing(null);
            showSuccess("Beszállító mentve.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title={t.confirmDeleteTitle}
          message={`Biztosan törli a(z) „${deleting.name}” beszállítót?`}
          isDangerous
          onCancel={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await suppliersApi.deleteSupplier(deleting.id);
              invalidate();
              showSuccess("Beszállító törölve.");
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

interface SupplierFormModalProps {
  supplier: Supplier | null;
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

function SupplierFormModal({ supplier, onClose, onSaved, onError }: SupplierFormModalProps) {
  const [name, setName] = useState(supplier?.name ?? "");
  const [contactName, setContactName] = useState(supplier?.contact_name ?? "");
  const [email, setEmail] = useState(supplier?.email ?? "");
  const [phone, setPhone] = useState(supplier?.phone ?? "");
  const [address, setAddress] = useState(supplier?.address ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    const payload = {
      name,
      contact_name: contactName || null,
      email: email || null,
      phone: phone || null,
      address: address || null,
    };
    try {
      if (supplier) {
        await suppliersApi.updateSupplier(supplier.id, payload);
      } else {
        await suppliersApi.createSupplier(payload);
      }
      onSaved();
    } catch (err) {
      onError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title={supplier ? "Beszállító szerkesztése" : "Új beszállító"} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <Field label={t.name} htmlFor="sup-name" required>
          <input id="sup-name" value={name} onChange={(event) => setName(event.target.value)} required autoFocus />
        </Field>
        <div className="form-row">
          <Field label="Kapcsolattartó" htmlFor="sup-contact">
            <input id="sup-contact" value={contactName ?? ""} onChange={(event) => setContactName(event.target.value)} />
          </Field>
          <Field label="Telefon" htmlFor="sup-phone">
            <input id="sup-phone" value={phone ?? ""} onChange={(event) => setPhone(event.target.value)} />
          </Field>
        </div>
        <Field label="E-mail" htmlFor="sup-email">
          <input id="sup-email" type="email" value={email ?? ""} onChange={(event) => setEmail(event.target.value)} />
        </Field>
        <Field label="Cím" htmlFor="sup-address">
          <textarea id="sup-address" value={address ?? ""} onChange={(event) => setAddress(event.target.value)} />
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
