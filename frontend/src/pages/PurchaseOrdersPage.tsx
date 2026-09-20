import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as productsApi from "../api/products";
import * as purchaseOrdersApi from "../api/purchaseOrders";
import type { PurchaseOrderLineInput, PurchaseOrderReceiveLineInput } from "../api/purchaseOrders";
import * as suppliersApi from "../api/suppliers";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { ClipboardIcon, DownloadIcon, PlusIcon, TrashIcon } from "../components/ui/icons";
import { Modal } from "../components/ui/Modal";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { t } from "../i18n/strings";
import { getErrorMessage } from "../lib/errors";
import { formatAmount, formatDateTime } from "../lib/format";
import { purchaseOrderStatusBadgeKind, purchaseOrderStatusLabels } from "../lib/orderLabels";
import type { Product, PurchaseOrder, PurchaseOrderStatus, Supplier, Warehouse } from "../types";

const LIMIT = 20;
const STATUS_OPTIONS: PurchaseOrderStatus[] = ["draft", "submitted", "partially_received", "received", "cancelled"];

export function PurchaseOrdersPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<PurchaseOrderStatus | "">("");
  const [creating, setCreating] = useState(false);
  const [viewing, setViewing] = useState<PurchaseOrder | null>(null);
  const [cancelling, setCancelling] = useState<PurchaseOrder | null>(null);

  const suppliersQuery = useQuery({ queryKey: ["suppliers", "for-select"], queryFn: () => suppliersApi.listSuppliers({ limit: 200 }) });
  const warehousesQuery = useQuery({ queryKey: ["warehouses", "for-select"], queryFn: () => warehousesApi.listWarehouses({ limit: 200 }) });
  const productsQuery = useQuery({ queryKey: ["products", "for-select"], queryFn: () => productsApi.listProducts({ limit: 200 }) });
  const suppliers = suppliersQuery.data?.items ?? [];
  const warehouses = warehousesQuery.data?.items ?? [];
  const products = productsQuery.data?.items ?? [];

  const query = useQuery({
    queryKey: ["purchase-orders", { offset, statusFilter }],
    queryFn: () => purchaseOrdersApi.listPurchaseOrders({ offset, limit: LIMIT, status: statusFilter || undefined }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
    queryClient.invalidateQueries({ queryKey: ["stock"] });
    queryClient.invalidateQueries({ queryKey: ["movements"] });
  }

  async function refreshViewing(order: PurchaseOrder) {
    setViewing(await purchaseOrdersApi.getPurchaseOrder(order.id));
  }

  const columns: Column<PurchaseOrder>[] = [
    { key: "id", header: "Azonosító", render: (row) => <span className="mono">{`PO-${row.id}`}</span> },
    { key: "supplier", header: "Beszállító", render: (row) => row.supplier.name },
    { key: "warehouse", header: "Raktár", render: (row) => row.warehouse.name },
    {
      key: "status",
      header: "Állapot",
      render: (row) => <Badge kind={purchaseOrderStatusBadgeKind[row.status]}>{purchaseOrderStatusLabels[row.status]}</Badge>,
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
        title="Beszerzési rendelések"
        subtitle="Beszállítóktól rendelt utánpótlás."
        actions={
          <div style={{ display: "flex", gap: "0.7rem" }}>
            <Button
              variant="ghost"
              onClick={() =>
                purchaseOrdersApi
                  .exportPurchaseOrders({ status: statusFilter || undefined })
                  .catch((err) => showError(getErrorMessage(err)))
              }
            >
              <DownloadIcon />
              CSV exportálás
            </Button>
            {isAdmin && (
              <Button onClick={() => setCreating(true)}>
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
            <Field label="Állapot" htmlFor="po-status">
              <select
                id="po-status"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as PurchaseOrderStatus | "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {purchaseOrderStatusLabels[status]}
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
        <PurchaseOrderFormModal
          suppliers={suppliers}
          warehouses={warehouses}
          products={products}
          onClose={() => setCreating(false)}
          onSaved={() => {
            invalidate();
            setCreating(false);
            showSuccess("Beszerzési rendelés létrehozva.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {viewing && (
        <PurchaseOrderDetailModal
          order={viewing}
          isAdmin={isAdmin}
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
          message={`Biztosan törli a(z) PO-${cancelling.id} beszerzési rendelést?`}
          isDangerous
          onCancel={() => setCancelling(null)}
          onConfirm={async () => {
            try {
              const updated = await purchaseOrdersApi.cancelPurchaseOrder(cancelling.id);
              invalidate();
              setViewing(updated);
              showSuccess("Beszerzési rendelés törölve.");
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
  unit_price: string;
}

function emptyLine(): LineDraft {
  return { product_id: "", quantity_ordered: 1, unit_price: "0.00" };
}

interface PurchaseOrderFormModalProps {
  suppliers: Supplier[];
  warehouses: Warehouse[];
  products: Product[];
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

function PurchaseOrderFormModal({ suppliers, warehouses, products, onClose, onSaved, onError }: PurchaseOrderFormModalProps) {
  const [supplierId, setSupplierId] = useState<number | "">("");
  const [warehouseId, setWarehouseId] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([emptyLine()]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateLine(index: number, patch: Partial<LineDraft>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!supplierId || !warehouseId) return;
    const validLines: PurchaseOrderLineInput[] = lines
      .filter((line) => line.product_id !== "")
      .map((line) => ({
        product_id: line.product_id as number,
        quantity_ordered: line.quantity_ordered,
        unit_price: line.unit_price,
      }));
    if (validLines.length === 0) return;

    setIsSubmitting(true);
    try {
      await purchaseOrdersApi.createPurchaseOrder({
        supplier_id: supplierId,
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
    <Modal title="Új beszerzési rendelés" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <Field label="Beszállító" htmlFor="po-supplier" required>
            <select id="po-supplier" value={supplierId} onChange={(event) => setSupplierId(event.target.value ? Number(event.target.value) : "")} required>
              <option value="" disabled>
                Válasszon…
              </option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Raktár" htmlFor="po-warehouse" required>
            <select id="po-warehouse" value={warehouseId} onChange={(event) => setWarehouseId(event.target.value ? Number(event.target.value) : "")} required>
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
        <Field label="Megjegyzés" htmlFor="po-notes">
          <textarea id="po-notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </Field>

        <div className="field">
          <label>Tételek *</label>
          <div className="line-items">
            {lines.map((line, index) => (
              <div className="line-item-row line-item-row--priced" key={index}>
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
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.unit_price}
                  onChange={(event) => updateLine(index, { unit_price: event.target.value })}
                  aria-label="Beszerzési egységár"
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

interface PurchaseOrderDetailModalProps {
  order: PurchaseOrder;
  isAdmin: boolean;
  onClose: () => void;
  onChanged: (message: string) => void;
  onCancelRequested: () => void;
  onError: (err: unknown) => void;
}

function PurchaseOrderDetailModal({ order, isAdmin, onClose, onChanged, onCancelRequested, onError }: PurchaseOrderDetailModalProps) {
  const [isReceiving, setIsReceiving] = useState(false);
  const [receiveQuantities, setReceiveQuantities] = useState<Record<number, number>>({});
  const [isBusy, setIsBusy] = useState(false);

  function startReceiving() {
    const initial: Record<number, number> = {};
    for (const line of order.lines) {
      const remaining = line.quantity_ordered - line.quantity_received;
      if (remaining > 0) initial[line.id] = remaining;
    }
    setReceiveQuantities(initial);
    setIsReceiving(true);
  }

  async function handleSubmit() {
    setIsBusy(true);
    try {
      await purchaseOrdersApi.submitPurchaseOrder(order.id);
      onChanged("Beszerzési rendelés beküldve.");
    } catch (err) {
      onError(err);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReceive(event: FormEvent) {
    event.preventDefault();
    const lines: PurchaseOrderReceiveLineInput[] = Object.entries(receiveQuantities)
      .filter(([, quantity]) => quantity > 0)
      .map(([lineId, quantity]) => ({ purchase_order_line_id: Number(lineId), quantity }));
    if (lines.length === 0) return;

    setIsBusy(true);
    try {
      await purchaseOrdersApi.receivePurchaseOrder(order.id, lines);
      setIsReceiving(false);
      onChanged("Átvétel rögzítve.");
    } catch (err) {
      onError(err);
    } finally {
      setIsBusy(false);
    }
  }

  const canSubmit = isAdmin && order.status === "draft";
  const canCancel = isAdmin && (order.status === "draft" || order.status === "submitted");
  const canReceive = order.status === "submitted" || order.status === "partially_received";

  return (
    <Modal title={`PO-${order.id}`} onClose={onClose}>
      <div className="detail-meta">
        <div>
          <strong>Beszállító:</strong> {order.supplier.name}
        </div>
        <div>
          <strong>Raktár:</strong> {order.warehouse.name}
        </div>
        <div>
          <strong>Állapot:</strong> <Badge kind={purchaseOrderStatusBadgeKind[order.status]}>{purchaseOrderStatusLabels[order.status]}</Badge>
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
              <th className="num">Átvéve</th>
              <th className="num">Egységár</th>
              {isReceiving && <th className="num">Átvétel most</th>}
            </tr>
          </thead>
          <tbody>
            {order.lines.map((line) => (
              <tr key={line.id}>
                <td>
                  {line.product.name} <span className="text-faint mono">{line.product.sku}</span>
                </td>
                <td className="num">{line.quantity_ordered}</td>
                <td className="num">{line.quantity_received}</td>
                <td className="num">{formatAmount(line.unit_price)}</td>
                {isReceiving && (
                  <td className="num">
                    {line.quantity_ordered - line.quantity_received > 0 ? (
                      <input
                        type="number"
                        min="0"
                        max={line.quantity_ordered - line.quantity_received}
                        step="1"
                        style={{ width: "5rem" }}
                        value={receiveQuantities[line.id] ?? 0}
                        onChange={(event) =>
                          setReceiveQuantities((prev) => ({ ...prev, [line.id]: Number(event.target.value) }))
                        }
                      />
                    ) : (
                      <span className="text-faint">—</span>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isReceiving ? (
        <form onSubmit={handleReceive}>
          <div className="form-actions">
            <Button type="button" variant="ghost" onClick={() => setIsReceiving(false)}>
              {t.cancel}
            </Button>
            <Button type="submit" disabled={isBusy}>
              Átvétel mentése
            </Button>
          </div>
        </form>
      ) : (
        <div className="form-actions">
          {canCancel && (
            <Button variant="danger" onClick={onCancelRequested} disabled={isBusy}>
              {t.delete}
            </Button>
          )}
          {canSubmit && (
            <Button variant="verdigris" onClick={handleSubmit} disabled={isBusy}>
              Beküldés
            </Button>
          )}
          {canReceive && (
            <Button onClick={startReceiving} disabled={isBusy}>
              <ClipboardIcon /> Átvétel rögzítése
            </Button>
          )}
        </div>
      )}
    </Modal>
  );
}
