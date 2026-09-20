import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as customerOrdersApi from "../api/customerOrders";
import * as shipmentsApi from "../api/shipments";
import type { ShipmentLineInput } from "../api/shipments";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { GearSpinner } from "../components/ui/GearSpinner";
import { PlusIcon } from "../components/ui/icons";
import { Modal } from "../components/ui/Modal";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { t } from "../i18n/strings";
import { getErrorMessage } from "../lib/errors";
import { formatDateTime } from "../lib/format";
import { shipmentStatusBadgeKind, shipmentStatusLabels } from "../lib/orderLabels";
import type { CustomerOrder, Shipment, ShipmentStatus } from "../types";

const LIMIT = 20;
const STATUS_OPTIONS: ShipmentStatus[] = ["pending", "in_transit", "delivered", "cancelled"];

export function ShipmentsPage() {
  const { isAdmin } = useAuth();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<ShipmentStatus | "">("");
  const [creating, setCreating] = useState(false);
  const [viewing, setViewing] = useState<Shipment | null>(null);
  const [cancelling, setCancelling] = useState<Shipment | null>(null);

  const query = useQuery({
    queryKey: ["shipments", { offset, statusFilter }],
    queryFn: () => shipmentsApi.listShipments({ offset, limit: LIMIT, status: statusFilter || undefined }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["shipments"] });
    queryClient.invalidateQueries({ queryKey: ["customer-orders"] });
    queryClient.invalidateQueries({ queryKey: ["stock"] });
    queryClient.invalidateQueries({ queryKey: ["movements"] });
  }

  async function refreshViewing(shipment: Shipment) {
    setViewing(await shipmentsApi.getShipment(shipment.id));
  }

  const columns: Column<Shipment>[] = [
    { key: "id", header: "Azonosító", render: (row) => <span className="mono">{`SHP-${row.id}`}</span> },
    { key: "order", header: "Rendelés", render: (row) => <span className="mono">{`CO-${row.customer_order_id}`}</span> },
    { key: "carrier", header: "Fuvarozó", render: (row) => row.carrier || <span className="text-faint">—</span> },
    { key: "tracking", header: "Nyomkövetési szám", render: (row) => row.tracking_number || <span className="text-faint">—</span> },
    {
      key: "status",
      header: "Állapot",
      render: (row) => <Badge kind={shipmentStatusBadgeKind[row.status]}>{shipmentStatusLabels[row.status]}</Badge>,
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
        title="Szállítmányok"
        subtitle="Vevői rendelésekhez tartozó fizikai szállítmányok."
        actions={
          <Button onClick={() => setCreating(true)}>
            <PlusIcon />
            {t.create}
          </Button>
        }
      />
      <div className="page-content">
        <Panel>
          <div className="filters-bar">
            <Field label="Állapot" htmlFor="shp-status">
              <select
                id="shp-status"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as ShipmentStatus | "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {shipmentStatusLabels[status]}
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
        <ShipmentFormModal
          onClose={() => setCreating(false)}
          onSaved={() => {
            invalidate();
            setCreating(false);
            showSuccess("Szállítmány létrehozva.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />
      )}

      {viewing && (
        <ShipmentDetailModal
          shipment={viewing}
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
          title="Szállítmány törlése"
          message={`Biztosan törli a(z) SHP-${cancelling.id} szállítmányt? A készlet visszakerül a raktárba.`}
          isDangerous
          onCancel={() => setCancelling(null)}
          onConfirm={async () => {
            try {
              const updated = await shipmentsApi.cancelShipment(cancelling.id);
              invalidate();
              setViewing(updated);
              showSuccess("Szállítmány törölve, a készlet visszaforgatva.");
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

interface ShipmentFormModalProps {
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

function ShipmentFormModal({ onClose, onSaved, onError }: ShipmentFormModalProps) {
  const confirmedQuery = useQuery({
    queryKey: ["customer-orders", "shippable", "confirmed"],
    queryFn: () => customerOrdersApi.listCustomerOrders({ status: "confirmed", limit: 100 }),
  });
  const partialQuery = useQuery({
    queryKey: ["customer-orders", "shippable", "partially_shipped"],
    queryFn: () => customerOrdersApi.listCustomerOrders({ status: "partially_shipped", limit: 100 }),
  });
  const shippableOrders = [...(confirmedQuery.data?.items ?? []), ...(partialQuery.data?.items ?? [])];

  const [orderId, setOrderId] = useState<number | "">("");
  const orderQuery = useQuery({
    queryKey: ["customer-orders", "detail", orderId],
    queryFn: () => customerOrdersApi.getCustomerOrder(orderId as number),
    enabled: orderId !== "",
  });
  const order = orderId === "" ? null : (orderQuery.data ?? null);

  return (
    <Modal title="Új szállítmány" onClose={onClose}>
      <Field label="Vevői rendelés" htmlFor="shp-order" required>
        <select id="shp-order" value={orderId} onChange={(event) => setOrderId(event.target.value ? Number(event.target.value) : "")} required>
          <option value="" disabled>
            Válasszon…
          </option>
          {shippableOrders.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {`CO-${candidate.id} — ${candidate.customer.name}`}
            </option>
          ))}
        </select>
        {shippableOrders.length === 0 && !confirmedQuery.isLoading && !partialQuery.isLoading && (
          <div className="hint">Nincs visszaigazolt, szállításra váró vevői rendelés.</div>
        )}
      </Field>

      {orderQuery.isLoading && <GearSpinner label={t.loading} />}

      {order && !orderQuery.isLoading && (
        <ShipmentDetailsForm key={order.id} order={order} onClose={onClose} onSaved={onSaved} onError={onError} />
      )}
    </Modal>
  );
}

interface ShipmentDetailsFormProps {
  order: CustomerOrder;
  onClose: () => void;
  onSaved: () => void;
  onError: (err: unknown) => void;
}

// Keyed by order.id from the parent, so switching orders remounts this component instead of
// needing an effect to reset `quantities` when the selected order changes.
function ShipmentDetailsForm({ order, onClose, onSaved, onError }: ShipmentDetailsFormProps) {
  const [carrier, setCarrier] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [quantities, setQuantities] = useState<Record<number, number>>(() => {
    const initial: Record<number, number> = {};
    for (const line of order.lines) {
      const remaining = line.quantity_ordered - line.quantity_shipped;
      if (remaining > 0) initial[line.id] = remaining;
    }
    return initial;
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const lines: ShipmentLineInput[] = Object.entries(quantities)
      .filter(([, quantity]) => quantity > 0)
      .map(([lineId, quantity]) => ({ customer_order_line_id: Number(lineId), quantity }));
    if (lines.length === 0) return;

    setIsSubmitting(true);
    try {
      await shipmentsApi.createShipment({
        customer_order_id: order.id,
        carrier: carrier || null,
        tracking_number: trackingNumber || null,
        lines,
      });
      onSaved();
    } catch (err) {
      onError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-row">
        <Field label="Fuvarozó" htmlFor="shp-carrier">
          <input id="shp-carrier" value={carrier} onChange={(event) => setCarrier(event.target.value)} />
        </Field>
        <Field label="Nyomkövetési szám" htmlFor="shp-tracking">
          <input id="shp-tracking" value={trackingNumber} onChange={(event) => setTrackingNumber(event.target.value)} />
        </Field>
      </div>

      <div className="field">
        <label>Szállítandó tételek *</label>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Termék</th>
                <th className="num">Hátralévő</th>
                <th className="num">Szállítás most</th>
              </tr>
            </thead>
            <tbody>
              {order.lines.map((line) => {
                const remaining = line.quantity_ordered - line.quantity_shipped;
                return (
                  <tr key={line.id}>
                    <td>
                      {line.product.name} <span className="text-faint mono">{line.product.sku}</span>
                    </td>
                    <td className="num">{remaining}</td>
                    <td className="num">
                      {remaining > 0 ? (
                        <input
                          type="number"
                          min="0"
                          max={remaining}
                          step="1"
                          style={{ width: "5rem" }}
                          value={quantities[line.id] ?? 0}
                          onChange={(event) => setQuantities((prev) => ({ ...prev, [line.id]: Number(event.target.value) }))}
                        />
                      ) : (
                        <span className="text-faint">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="form-actions">
        <Button type="button" variant="ghost" onClick={onClose}>
          {t.cancel}
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {t.save}
        </Button>
      </div>
    </form>
  );
}

interface ShipmentDetailModalProps {
  shipment: Shipment;
  isAdmin: boolean;
  onClose: () => void;
  onChanged: (message: string) => void;
  onCancelRequested: () => void;
  onError: (err: unknown) => void;
}

function ShipmentDetailModal({ shipment, isAdmin, onClose, onChanged, onCancelRequested, onError }: ShipmentDetailModalProps) {
  const [isBusy, setIsBusy] = useState(false);

  async function handleDispatch() {
    setIsBusy(true);
    try {
      await shipmentsApi.dispatchShipment(shipment.id);
      onChanged("Szállítmány útnak indítva.");
    } catch (err) {
      onError(err);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDeliver() {
    setIsBusy(true);
    try {
      await shipmentsApi.deliverShipment(shipment.id);
      onChanged("Szállítmány kiszállítva.");
    } catch (err) {
      onError(err);
    } finally {
      setIsBusy(false);
    }
  }

  const canDispatch = shipment.status === "pending";
  const canDeliver = shipment.status === "in_transit";
  const canCancel = isAdmin && (shipment.status === "pending" || shipment.status === "in_transit");

  return (
    <Modal title={`SHP-${shipment.id}`} onClose={onClose}>
      <div className="detail-meta">
        <div>
          <strong>Rendelés:</strong> <span className="mono">{`CO-${shipment.customer_order_id}`}</span>
        </div>
        <div>
          <strong>Állapot:</strong> <Badge kind={shipmentStatusBadgeKind[shipment.status]}>{shipmentStatusLabels[shipment.status]}</Badge>
        </div>
        <div>
          <strong>Fuvarozó:</strong> {shipment.carrier || <span className="text-faint">—</span>}
        </div>
        <div>
          <strong>Nyomkövetési szám:</strong> {shipment.tracking_number || <span className="text-faint">—</span>}
        </div>
        <div>
          <strong>Létrehozta:</strong> {shipment.created_by.full_name}
        </div>
        {shipment.shipped_at && (
          <div>
            <strong>Útnak indítva:</strong> {formatDateTime(shipment.shipped_at)}
          </div>
        )}
        {shipment.delivered_at && (
          <div>
            <strong>Kiszállítva:</strong> {formatDateTime(shipment.delivered_at)}
          </div>
        )}
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Termék</th>
              <th className="num">Mennyiség</th>
            </tr>
          </thead>
          <tbody>
            {shipment.lines.map((line) => (
              <tr key={line.id}>
                <td>
                  {line.product.name} <span className="text-faint mono">{line.product.sku}</span>
                </td>
                <td className="num">{line.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="form-actions">
        {canCancel && (
          <Button variant="danger" onClick={onCancelRequested} disabled={isBusy}>
            {t.delete}
          </Button>
        )}
        {canDispatch && (
          <Button variant="verdigris" onClick={handleDispatch} disabled={isBusy}>
            Útnak indítás
          </Button>
        )}
        {canDeliver && (
          <Button onClick={handleDeliver} disabled={isBusy}>
            Kiszállítva
          </Button>
        )}
      </div>
    </Modal>
  );
}
