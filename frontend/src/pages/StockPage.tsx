import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import * as productsApi from "../api/products";
import * as stockApi from "../api/stock";
import type { StockInInput } from "../api/stock";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { Button } from "../components/ui/Button";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { TransferIcon } from "../components/ui/icons";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { useToast } from "../context/ToastContext";
import { getErrorMessage } from "../lib/errors";
import { formatDateTime } from "../lib/format";
import type { Product, Stock, StockMovement, Warehouse } from "../types";

const LIMIT = 20;

type OperationKind = "in" | "out" | "transfer";

const operationLabels: Record<OperationKind, string> = {
  in: "Bevételezés",
  out: "Kiadás",
  transfer: "Áthelyezés",
};

export function StockPage() {
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();

  const [offset, setOffset] = useState(0);
  const [productFilter, setProductFilter] = useState<number | "">("");
  const [warehouseFilter, setWarehouseFilter] = useState<number | "">("");

  const productsQuery = useQuery({ queryKey: ["products", "for-select"], queryFn: () => productsApi.listProducts({ limit: 200 }) });
  const warehousesQuery = useQuery({ queryKey: ["warehouses", "for-select"], queryFn: () => warehousesApi.listWarehouses({ limit: 200 }) });
  const products = productsQuery.data?.items ?? [];
  const warehouses = warehousesQuery.data?.items ?? [];

  const stockQuery = useQuery({
    queryKey: ["stock", { offset, productFilter, warehouseFilter }],
    queryFn: () =>
      stockApi.listStock({
        offset,
        limit: LIMIT,
        product_id: productFilter || undefined,
        warehouse_id: warehouseFilter || undefined,
      }),
  });

  function invalidateStock() {
    queryClient.invalidateQueries({ queryKey: ["stock"] });
    queryClient.invalidateQueries({ queryKey: ["movements"] });
  }

  const columns: Column<Stock>[] = [
    {
      key: "product",
      header: "Termék",
      render: (row) => (
        <>
          {row.product.name} <span className="text-faint mono">{row.product.sku}</span>
        </>
      ),
    },
    { key: "warehouse", header: "Raktár", render: (row) => row.warehouse.name },
    { key: "quantity", header: "Mennyiség", numeric: true, render: (row) => row.quantity },
    { key: "updated", header: "Utolsó frissítés", render: (row) => formatDateTime(row.updated_at) },
  ];

  return (
    <>
      <PageHeader title="Készlet" subtitle="Aktuális készletszintek és készletmozgások rögzítése." />
      <div className="page-content">
        <StockOperationPanel
          products={products}
          warehouses={warehouses}
          onSuccess={() => {
            invalidateStock();
            showSuccess("Készletmozgás rögzítve.");
          }}
          onError={(err) => showError(getErrorMessage(err))}
        />

        <Panel>
          <div className="panel-header">
            <h3>Jelenlegi készlet</h3>
          </div>
          <div className="filters-bar">
            <Field label="Termék" htmlFor="stock-product-filter">
              <select
                id="stock-product-filter"
                value={productFilter}
                onChange={(event) => {
                  setProductFilter(event.target.value ? Number(event.target.value) : "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Raktár" htmlFor="stock-warehouse-filter">
              <select
                id="stock-warehouse-filter"
                value={warehouseFilter}
                onChange={(event) => {
                  setWarehouseFilter(event.target.value ? Number(event.target.value) : "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>
                    {warehouse.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <DataTable columns={columns} rows={stockQuery.data?.items ?? []} rowKey={(row) => row.id} isLoading={stockQuery.isLoading} />
          {stockQuery.data && <Pagination total={stockQuery.data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
        </Panel>
      </div>
    </>
  );
}

interface StockOperationPanelProps {
  products: Product[];
  warehouses: Warehouse[];
  onSuccess: () => void;
  onError: (err: unknown) => void;
}

interface WarehouseSelectProps {
  id: string;
  label: string;
  value: number | "";
  onChange: (value: number | "") => void;
  warehouses: Warehouse[];
}

// Shared by all three warehouse pickers below (single warehouse for in/out, from/to for
// transfer) - previously three separately hand-written, byte-identical <select> blocks.
function WarehouseSelect({ id, label, value, onChange, warehouses }: WarehouseSelectProps) {
  return (
    <Field label={label} htmlFor={id} required>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : "")}
        required
      >
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
  );
}

// stockIn/stockOut take the identical {product_id, warehouse_id, quantity, note} shape, so the
// "in" and "out" cases collapse into one lookup instead of two near-identical branches; transfer
// keeps its own branch below since its payload shape (from/to) genuinely differs.
const SINGLE_WAREHOUSE_OPS: Record<"in" | "out", (input: StockInInput) => Promise<StockMovement>> = {
  in: stockApi.stockIn,
  out: stockApi.stockOut,
};

function StockOperationPanel({ products, warehouses, onSuccess, onError }: StockOperationPanelProps) {
  const [kind, setKind] = useState<OperationKind>("in");
  const [productId, setProductId] = useState<number | "">("");
  const [warehouseId, setWarehouseId] = useState<number | "">("");
  const [fromWarehouseId, setFromWarehouseId] = useState<number | "">("");
  const [toWarehouseId, setToWarehouseId] = useState<number | "">("");
  const [quantity, setQuantity] = useState(1);
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function resetForm() {
    setProductId("");
    setWarehouseId("");
    setFromWarehouseId("");
    setToWarehouseId("");
    setQuantity(1);
    setNote("");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!productId) return;

    setIsSubmitting(true);
    try {
      if (kind === "transfer") {
        if (!fromWarehouseId || !toWarehouseId) return;
        await stockApi.stockTransfer({
          product_id: productId,
          from_warehouse_id: fromWarehouseId,
          to_warehouse_id: toWarehouseId,
          quantity,
          note: note || null,
        });
      } else {
        if (!warehouseId) return;
        await SINGLE_WAREHOUSE_OPS[kind]({ product_id: productId, warehouse_id: warehouseId, quantity, note: note || null });
      }
      resetForm();
      onSuccess();
    } catch (err) {
      onError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Panel>
      <div className="panel-header">
        <h3>
          <TransferIcon style={{ verticalAlign: "-3px", marginRight: "0.5rem" }} />
          Készletmozgás rögzítése
        </h3>
      </div>

      <div className="segmented" role="tablist">
        {(Object.keys(operationLabels) as OperationKind[]).map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={kind === k}
            className={`segmented-btn${kind === k ? " active" : ""}`}
            onClick={() => setKind(k)}
          >
            {operationLabels[k]}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        <Field label="Termék" htmlFor="op-product" required>
          <select id="op-product" value={productId} onChange={(event) => setProductId(event.target.value ? Number(event.target.value) : "")} required>
            <option value="" disabled>
              Válasszon…
            </option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} ({product.sku})
              </option>
            ))}
          </select>
        </Field>

        {kind !== "transfer" && (
          <WarehouseSelect id="op-warehouse" label="Raktár" value={warehouseId} onChange={setWarehouseId} warehouses={warehouses} />
        )}

        {kind === "transfer" && (
          <div className="form-row">
            <WarehouseSelect id="op-from" label="Honnan" value={fromWarehouseId} onChange={setFromWarehouseId} warehouses={warehouses} />
            <WarehouseSelect id="op-to" label="Hová" value={toWarehouseId} onChange={setToWarehouseId} warehouses={warehouses} />
          </div>
        )}

        <div className="form-row">
          <Field label="Mennyiség" htmlFor="op-quantity" required>
            <input
              id="op-quantity"
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(event) => setQuantity(Number(event.target.value))}
              required
            />
          </Field>
          <Field label="Megjegyzés" htmlFor="op-note">
            <input id="op-note" value={note} onChange={(event) => setNote(event.target.value)} />
          </Field>
        </div>

        <div className="form-actions">
          <Button type="submit" disabled={isSubmitting}>
            {operationLabels[kind]}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
