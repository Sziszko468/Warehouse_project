import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as categoriesApi from "../api/categories";
import * as productsApi from "../api/products";
import * as suppliersApi from "../api/suppliers";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { DownloadIcon, EditIcon, PlusIcon, TrashIcon } from "../components/ui/icons";
import { Modal } from "../components/ui/Modal";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { t } from "../i18n/strings";
import { getErrorMessage } from "../lib/errors";
import { formatAmount } from "../lib/format";
import type { Category, Product, Supplier } from "../types";

const LIMIT = 20;

export function ProductsPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | "">("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  const [deleting, setDeleting] = useState<Product | null>(null);

  const categoriesQuery = useQuery({
    queryKey: ["categories", "for-select"],
    queryFn: () => categoriesApi.listCategories({ limit: 200 }),
  });
  const suppliersQuery = useQuery({
    queryKey: ["suppliers", "for-select"],
    queryFn: () => suppliersApi.listSuppliers({ limit: 200 }),
  });
  const categories = categoriesQuery.data?.items ?? [];
  const suppliers = suppliersQuery.data?.items ?? [];
  const categoryById = new Map(categories.map((category) => [category.id, category]));

  const query = useQuery({
    queryKey: ["products", { offset, search, categoryFilter, includeInactive }],
    queryFn: () =>
      productsApi.listProducts({
        offset,
        limit: LIMIT,
        search: search || undefined,
        category_id: categoryFilter || undefined,
        include_inactive: includeInactive,
      }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["products"] });
    // min_stock_threshold lives on the product but drives the backend's low-stock computation,
    // so a product edit can change which stock rows count as low without any stock row itself
    // changing - the low-stock widget/page would otherwise show stale data until it happens to
    // remount.
    queryClient.invalidateQueries({ queryKey: ["stock"] });
  }

  const columns: Column<Product>[] = [
    { key: "sku", header: "Cikkszám", render: (row) => <span className="mono">{row.sku}</span> },
    { key: "name", header: t.name, render: (row) => row.name },
    { key: "category", header: "Kategória", render: (row) => categoryById.get(row.category_id)?.name ?? "—" },
    { key: "price", header: "Egységár", numeric: true, render: (row) => formatAmount(row.unit_price) },
    { key: "threshold", header: "Min. készlet", numeric: true, render: (row) => row.min_stock_threshold },
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
        title="Termékek"
        subtitle="A raktárkészlet alapját képező termékek."
        actions={
          <div style={{ display: "flex", gap: "0.7rem" }}>
            <Button
              variant="ghost"
              onClick={() =>
                productsApi
                  .exportProducts({ search: search || undefined, category_id: categoryFilter || undefined, include_inactive: includeInactive })
                  .catch((err) => showError(getErrorMessage(err)))
              }
            >
              <DownloadIcon />
              CSV exportálás
            </Button>
            {isAdmin && (
              <Button onClick={() => setEditing("new")}>
                <PlusIcon />
                {t.create}
              </Button>
            )}
          </div>
        }
      />
      <div className="page-content">
        <Panel>
          <div className="filters-bar">
            <Field label={t.search} htmlFor="search">
              <input
                id="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setOffset(0);
                }}
                placeholder="Név vagy cikkszám…"
              />
            </Field>
            <Field label="Kategória" htmlFor="categoryFilter">
              <select
                id="categoryFilter"
                value={categoryFilter}
                onChange={(event) => {
                  setCategoryFilter(event.target.value ? Number(event.target.value) : "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </Field>
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
        <ProductFormModal
          product={editing === "new" ? null : editing}
          categories={categories}
          suppliers={suppliers}
          onClose={() => setEditing(null)}
          onSaved={() => {
            invalidate();
            setEditing(null);
            showSuccess("Termék mentve.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title={t.confirmDeleteTitle}
          message={`Biztosan törli a(z) „${deleting.name}” terméket?`}
          isDangerous
          onCancel={() => setDeleting(null)}
          onConfirm={async () => {
            try {
              await productsApi.deleteProduct(deleting.id);
              invalidate();
              showSuccess("Termék törölve.");
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

interface ProductFormModalProps {
  product: Product | null;
  categories: Category[];
  suppliers: Supplier[];
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

function ProductFormModal({ product, categories, suppliers, onClose, onSaved, onError }: ProductFormModalProps) {
  const [sku, setSku] = useState(product?.sku ?? "");
  const [name, setName] = useState(product?.name ?? "");
  const [description, setDescription] = useState(product?.description ?? "");
  const [categoryId, setCategoryId] = useState<number | "">(product?.category_id ?? "");
  const [supplierId, setSupplierId] = useState<number | "">(product?.supplier_id ?? "");
  const [unitPrice, setUnitPrice] = useState(product?.unit_price ?? "0.00");
  const [minStockThreshold, setMinStockThreshold] = useState(product?.min_stock_threshold ?? 0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!categoryId) return;
    setIsSubmitting(true);
    const payload = {
      sku,
      name,
      description: description || null,
      category_id: categoryId,
      supplier_id: supplierId || null,
      unit_price: unitPrice,
      min_stock_threshold: minStockThreshold,
    };
    try {
      if (product) {
        await productsApi.updateProduct(product.id, payload);
      } else {
        await productsApi.createProduct(payload);
      }
      onSaved();
    } catch (err) {
      onError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title={product ? "Termék szerkesztése" : "Új termék"} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <Field label="Cikkszám (SKU)" htmlFor="prod-sku" required>
            <input id="prod-sku" value={sku} onChange={(event) => setSku(event.target.value)} required autoFocus />
          </Field>
          <Field label={t.name} htmlFor="prod-name" required>
            <input id="prod-name" value={name} onChange={(event) => setName(event.target.value)} required />
          </Field>
        </div>
        <Field label={t.description} htmlFor="prod-desc">
          <textarea id="prod-desc" value={description ?? ""} onChange={(event) => setDescription(event.target.value)} />
        </Field>
        <div className="form-row">
          <Field label="Kategória" htmlFor="prod-category" required>
            <select
              id="prod-category"
              value={categoryId}
              onChange={(event) => setCategoryId(event.target.value ? Number(event.target.value) : "")}
              required
            >
              <option value="" disabled>
                Válasszon…
              </option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Beszállító" htmlFor="prod-supplier">
            <select
              id="prod-supplier"
              value={supplierId}
              onChange={(event) => setSupplierId(event.target.value ? Number(event.target.value) : "")}
            >
              <option value="">Nincs megadva</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="form-row">
          <Field label="Egységár" htmlFor="prod-price" required>
            <input
              id="prod-price"
              type="number"
              step="0.01"
              min="0"
              value={unitPrice}
              onChange={(event) => setUnitPrice(event.target.value)}
              required
            />
          </Field>
          <Field label="Minimális készletszint" htmlFor="prod-threshold" hint="Ez alatt jelez a rendszer alacsony készletet.">
            <input
              id="prod-threshold"
              type="number"
              min="0"
              step="1"
              value={minStockThreshold}
              onChange={(event) => setMinStockThreshold(Number(event.target.value))}
            />
          </Field>
        </div>
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
