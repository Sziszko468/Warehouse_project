import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as categoriesApi from "../api/categories";
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
import type { Category } from "../types";

const LIMIT = 20;

export function CategoriesPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [editing, setEditing] = useState<Category | "new" | null>(null);
  const [deleting, setDeleting] = useState<Category | null>(null);

  const query = useQuery({
    queryKey: ["categories", { offset, includeInactive }],
    queryFn: () => categoriesApi.listCategories({ offset, limit: LIMIT, include_inactive: includeInactive }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["categories"] });
  }

  const columns: Column<Category>[] = [
    { key: "name", header: t.name, render: (row) => row.name },
    {
      key: "description",
      header: t.description,
      render: (row) => row.description || <span className="text-faint">—</span>,
    },
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
        title="Kategóriák"
        subtitle="Termékek csoportosítása kategóriákba."
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
        <CategoryFormModal
          category={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            invalidate();
            setEditing(null);
            showSuccess("Kategória mentve.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title={t.confirmDeleteTitle}
          message={`Biztosan törli a(z) „${deleting.name}” kategóriát?`}
          isDangerous
          onCancel={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await categoriesApi.deleteCategory(deleting.id);
              invalidate();
              showSuccess("Kategória törölve.");
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

interface CategoryFormModalProps {
  category: Category | null;
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

function CategoryFormModal({ category, onClose, onSaved, onError }: CategoryFormModalProps) {
  const [name, setName] = useState(category?.name ?? "");
  const [description, setDescription] = useState(category?.description ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      if (category) {
        await categoriesApi.updateCategory(category.id, { name, description: description || null });
      } else {
        await categoriesApi.createCategory({ name, description: description || null });
      }
      onSaved();
    } catch (err) {
      onError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title={category ? "Kategória szerkesztése" : "Új kategória"} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <Field label={t.name} htmlFor="cat-name" required>
          <input id="cat-name" value={name} onChange={(event) => setName(event.target.value)} required autoFocus />
        </Field>
        <Field label={t.description} htmlFor="cat-desc">
          <textarea id="cat-desc" value={description ?? ""} onChange={(event) => setDescription(event.target.value)} />
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
