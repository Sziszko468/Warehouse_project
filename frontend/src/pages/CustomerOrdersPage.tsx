import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as customerOrdersApi from "../api/customerOrders";
import type { CustomerOrderLineInput } from "../api/customerOrders";
import * as customersApi from "../api/customers";
import * as productsApi from "../api/products";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { DownloadIcon, PlusIcon, TrashIcon } from "../components/ui/icons";
import { Modal } from "../components/ui/Modal";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { useToast } from "../context/ToastContext";
import { t } from "../i18n/strings";
import { getErrorMessage } from "../lib/errors";
import { formatAmount, formatDateTime } from "../lib/format";
import { customerOrderStatusBadgeKind, customerOrderStatusLabels } from "../lib/orderLabels";
import type { Customer, CustomerOrder, CustomerOrderStatus, Product, Warehouse } from "../types";

const LIMIT = 20;
const STATUS_OPTIONS: CustomerOrderStatus[] = ["draft", "confirmed", "partially_shipped", "shipped", "cancelled"];

export function CustomerOrdersPage() {
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<CustomerOrderStatus | "">("");
  const [creating, setCreating] = useState(false);
  const [viewing, setViewing] = useState<CustomerOrder | null>(null);
  const [cancelling, setCancelling] = useState<CustomerOrder | null>(null);

  const customersQuery = useQuery({ queryKey: ["customers", "for-select"], queryFn: () => customersApi.listCustomers({ limit: 200 }) });
  const warehousesQuery = useQuery({ queryKey: ["warehouses", "for-select"], queryFn: () => warehousesApi.listWarehouses({ limit: 200 }) });
  const productsQuery = useQuery({ queryKey: ["products", "for-select"], queryFn: () => productsApi.listProducts({ limit: 200 }) });
  const customers = customersQuery.data?.items ?? [];
  const warehouses = warehousesQuery.data?.items ?? [];
  const products = productsQuery.data?.items ?? [];

  const query = useQuery({
    queryKey: ["customer-orders", { offset, statusFilter }],
    queryFn: () => customerOrdersApi.listCustomerOrders({ offset, limit: LIMIT, status: statusFilter || undefined }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["customer-orders"] });
    queryClient.invalidateQueries({ queryKey: ["stock"] });
  }

  async function refreshViewing(order: CustomerOrder) {
    setViewing(await customerOrdersApi.getCustomerOrder(order.id));
  }

  const columns: Column<CustomerOrder>[] = [
    { key: "id", header: "Azonosító", render: (row) => <span className="mono">{`CO-${row.id}`}</span> },
    { key: "customer", header: "Vevő", render: (row) => row.customer.name },
    { key: "warehouse", header: "Raktár", render: (row) => row.warehouse.name },
    {
      key: "status",
      header: "Állapot",
      render: (row) => <Badge kind={customerOrderStatusBadgeKind[row.status]}>{customerOrderStatusLabels[row.status]}</Badge>,
    },
    { key: "created", header: "Létrehozva", render: (row) => formatDateTime(row.created_at) },
    {
      key: "actions",
      header: t.actions,
      render: (row) => (
        <Button variant="ghost" size="sm" onClick={() => setViewing(row)}>
          Megtekintés
        </Button>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Vevői rendelések"
        subtitle="Vevők által leadott, raktárból kiszolgált rendelések."
        actions={
          <div style={{ display: "flex", gap: "0.7rem" }}>
            <Button
              variant="ghost"
              onClick={() =>
                customerOrdersApi
                  .exportCustomerOrders({ status: statusFilter || undefined })
                  .catch((err) => showError(getErrorMessage(err)))
              }
            >
              <DownloadIcon />
              CSV exportálás
            </Button>
            <Button onClick={() => setCreating(true)}>
              <PlusIcon />
              {t.create}
            </Button>
          </div>
        }
      />
      <div className="page-content">
        <Panel>
          <div className="filters-bar">
            <Field label="Állapot" htmlFor="co-status">
              <select
                id="co-status"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as CustomerOrderStatus | "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {customerOrderStatusLabels[status]}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <DataTable columns={columns} rows={query.data?.items ?? []} rowKey={(row) => row.id} isLoading={query.isLoading} />
          {query.data && <Pagination total={query.data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
        </Panel>
      </div>

      {creating && (
        <CustomerOrderFormModal
          customers={customers}
          warehouses={warehouses}
          products={products}
          onClose={() => setCreating(false)}
          onSaved={() => {
            invalidate();
            setCreating(false);
            showSuccess("Vevői rendelés létrehozva.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {viewing && (
        <CustomerOrderDetailModal
          order={viewing}
          onClose={() => setViewing(null)}
          onChanged={async (message) => {
            invalidate();
            await refreshViewing(viewing);
            showSuccess(message);
          }}
          onCancelRequested={() => setCancelling(viewing)}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {cancelling && (
        <ConfirmDialog
          title="Rendelés törlése"
          message={`Biztosan törli a(z) CO-${cancelling.id} vevői rendelést?`}
          isDangerous
          onCancel={() => setCancelling(null)}
          onConfirm={async () => {
            try {
              const updated = await customerOrdersApi.cancelCustomerOrder(cancelling.id);
              invalidate();
              setViewing(updated);
              showSuccess("Vevői rendelés törölve.");
            } catch (err) {
              showError(getErrorMessage(err));
            } finally {
              setCancelling(null);
            }
          }}
        />
      )}
    </>
  );
}

interface LineDraft {
  product_id: number | "";
  quantity_ordered: number;
}

function emptyLine(): LineDraft {
  return { product_id: "", quantity_ordered: 1 };
}

interface CustomerOrderFormModalProps {
  customers: Customer[];
  warehouses: Warehouse[];
  products: Product[];
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

function CustomerOrderFormModal({ customers, warehouses, products, onClose, onSaved, onError }: CustomerOrderFormModalProps) {
  const [customerId, setCustomerId] = useState<number | "">("");
  const [warehouseId, setWarehouseId] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([emptyLine()]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateLine(index: number, patch: Partial<LineDraft>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!customerId || !warehouseId) return;
    const validLines: CustomerOrderLineInput[] = lines
      .filter((line) => line.product_id !== "")
      .map((line) => ({ product_id: line.product_id as number, quantity_ordered: line.quantity_ordered }));
    if (validLines.length === 0) return;

    setIsSubmitting(true);
    try {
      await customerOrdersApi.createCustomerOrder({
        customer_id: customerId,
        warehouse_id: warehouseId,
        notes: notes || null,
        lines: validLines,
      });
      onSaved();
    } catch (err) {
      onError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title="Új vevői rendelés" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <Field label="Vevő" htmlFor="co-customer" required>
            <select id="co-customer" value={customerId} onChange={(event) => setCustomerId(event.target.value ? Number(event.target.value) : "")} required>
              <option value="" disabled>
                Válasszon…
              </option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Raktár" htmlFor="co-warehouse" required>
            <select id="co-warehouse" value={warehouseId} onChange={(event) => setWarehouseId(event.target.value ? Number(event.target.value) : "")} required>
              <option value="" disabled>
                Válasszon…
              </option>
              {warehouses.map((warehouse) => (
                <option key={warehouse.id} value={warehouse.id}>
                  {warehouse.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="Megjegyzés" htmlFor="co-notes">
          <textarea id="co-notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </Field>

        <div className="field">
          <label>Tételek *</label>
          <div className="line-items">
            {lines.map((line, index) => (
              <div className="line-item-row" key={index}>
                <select
                  value={line.product_id}
                  onChange={(event) => updateLine(index, { product_id: event.target.value ? Number(event.target.value) : "" })}
                  required
                >
                  <option value="" disabled>
                    Termék…
                  </option>
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.name} ({product.sku})
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={line.quantity_ordered}
                  onChange={(event) => updateLine(index, { quantity_ordered: Number(event.target.value) })}
                  aria-label="Mennyiség"
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="btn--icon"
                  onClick={() => setLines((prev) => prev.filter((_, i) => i !== index))}
                  disabled={lines.length === 1}
                  aria-label={t.delete}
                >
                  <TrashIcon />
                </Button>
              </div>
            ))}
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={() => setLines((prev) => [...prev, emptyLine()])}>
            <PlusIcon /> Tétel hozzáadása
          </Button>
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

interface CustomerOrderDetailModalProps {
  order: CustomerOrder;
  onClose: () => void;
  onChanged: (message: string) => void;
  onCancelRequested: () => void;
  onError: (err: unknown) => void;
}

function CustomerOrderDetailModal({ order, onClose, onChanged, onCancelRequested, onError }: CustomerOrderDetailModalProps) {
  const [isBusy, setIsBusy] = useState(false);

  async function handleConfirm() {
    setIsBusy(true);
    try {
      await customerOrdersApi.confirmCustomerOrder(order.id);
      onChanged("Vevői rendelés visszaigazolva — a készlet lefoglalva.");
    } catch (err) {
      onError(err);
    } finally {
      setIsBusy(false);
    }
  }

  const canConfirm = order.status === "draft";
  const canCancel = order.status === "draft" || order.status === "confirmed";
  const canShip = order.status === "confirmed" || order.status === "partially_shipped";

  return (
    <Modal title={`CO-${order.id}`} onClose={onClose}>
      <div className="detail-meta">
        <div>
          <strong>Vevő:</strong> {order.customer.name}
        </div>
        <div>
          <strong>Raktár:</strong> {order.warehouse.name}
        </div>
        <div>
          <strong>Állapot:</strong> <Badge kind={customerOrderStatusBadgeKind[order.status]}>{customerOrderStatusLabels[order.status]}</Badge>
        </div>
        <div>
          <strong>Létrehozta:</strong> {order.created_by.full_name}
        </div>
        {order.notes && (
          <div>
            <strong>Megjegyzés:</strong> {order.notes}
          </div>
        )}
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Termék</th>
              <th className="num">Rendelve</th>
              <th className="num">Szállítva</th>
              <th className="num">Egységár</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((line) => (
              <tr key={line.id}>
                <td>
                  {line.product.name} <span className="text-faint mono">{line.product.sku}</span>
                </td>
                <td className="num">{line.quantity_ordered}</td>
                <td className="num">{line.quantity_shipped}</td>
                <td className="num">{formatAmount(line.unit_price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {canShip && (
        <p className="hint" style={{ marginTop: "0.8rem" }}>
          A szállítmányok létrehozása és nyomon követése a „Szállítmányok” oldalon történik.
        </p>
      )}

      <div className="form-actions">
        {canCancel && (
          <Button variant="danger" onClick={onCancelRequested} disabled={isBusy}>
            {t.delete}
          </Button>
        )}
        {canConfirm && (
          <Button variant="verdigris" onClick={handleConfirm} disabled={isBusy}>
            Visszaigazolás
          </Button>
        )}
      </div>
    </Modal>
  );
}
