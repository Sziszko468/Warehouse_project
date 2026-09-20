import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import * as productsApi from "../api/products";
import * as stockApi from "../api/stock";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { Pagination } from "../components/ui/Pagination";
import { Panel } from "../components/ui/Panel";
import { t } from "../i18n/strings";
import { formatDateTime } from "../lib/format";
import { movementTypeBadgeKind, movementTypeLabels } from "../lib/movementLabels";
import type { MovementType, StockMovement } from "../types";

const LIMIT = 25;

export function MovementsPage() {
  const [offset, setOffset] = useState(0);
  const [productFilter, setProductFilter] = useState<number | "">("");
  const [warehouseFilter, setWarehouseFilter] = useState<number | "">("");
  const [typeFilter, setTypeFilter] = useState<MovementType | "">("");

  const productsQuery = useQuery({ queryKey: ["products", "for-select"], queryFn: () => productsApi.listProducts({ limit: 200 }) });
  const warehousesQuery = useQuery({ queryKey: ["warehouses", "for-select"], queryFn: () => warehousesApi.listWarehouses({ limit: 200 }) });
  const products = productsQuery.data?.items ?? [];
  const warehouses = warehousesQuery.data?.items ?? [];

  const query = useQuery({
    queryKey: ["movements", { offset, productFilter, warehouseFilter, typeFilter }],
    queryFn: () =>
      stockApi.listMovements({
        offset,
        limit: LIMIT,
        product_id: productFilter || undefined,
        warehouse_id: warehouseFilter || undefined,
        movement_type: typeFilter || undefined,
      }),
  });

  const columns: Column<StockMovement>[] = [
    { key: "created", header: "Időpont", render: (row) => formatDateTime(row.created_at) },
    {
      key: "product",
      header: "Termék",
      render: (row) => (
        <>
          {row.product.name} <span className="text-faint mono">{row.product.sku}</span>
        </>
      ),
    },
    {
      key: "type",
      header: "Típus",
      render: (row) => <Badge kind={movementTypeBadgeKind[row.movement_type]}>{movementTypeLabels[row.movement_type]}</Badge>,
    },
    { key: "quantity", header: "Mennyiség", numeric: true, render: (row) => row.quantity },
    { key: "from", header: "Honnan", render: (row) => row.from_warehouse?.name ?? <span className="text-faint">—</span> },
    { key: "to", header: "Hová", render: (row) => row.to_warehouse?.name ?? <span className="text-faint">—</span> },
    { key: "performer", header: "Végrehajtó", render: (row) => row.performed_by.full_name },
    { key: "note", header: "Megjegyzés", render: (row) => row.note ?? <span className="text-faint">—</span> },
  ];

  return (
    <>
      <PageHeader title="Mozgási napló" subtitle="A készletmozgások teljes, megváltoztathatatlan előzménye." />
      <div className="page-content">
        <Panel>
          <div className="filters-bar">
            <Field label="Termék" htmlFor="mv-product">
              <select
                id="mv-product"
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
            <Field label="Raktár" htmlFor="mv-warehouse">
              <select
                id="mv-warehouse"
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
            <Field label="Típus" htmlFor="mv-type">
              <select
                id="mv-type"
                value={typeFilter}
                onChange={(event) => {
                  setTypeFilter(event.target.value as MovementType | "");
                  setOffset(0);
                }}
              >
                <option value="">Összes</option>
                <option value="in">Bevételezés</option>
                <option value="out">Kiadás</option>
                <option value="transfer">Áthelyezés</option>
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
