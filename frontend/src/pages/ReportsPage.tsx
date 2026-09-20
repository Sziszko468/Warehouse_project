import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import * as categoriesApi from "../api/categories";
import * as reportsApi from "../api/reports";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { DataTable, type Column } from "../components/ui/DataTable";
import { Field } from "../components/ui/Field";
import { Panel } from "../components/ui/Panel";
import { t } from "../i18n/strings";
import { formatAmount } from "../lib/format";
import type {
  PurchaseActivityRow,
  SalesFulfillmentActivityRow,
  StockValuationByCategory,
  StockValuationByWarehouse,
} from "../api/reports";

export function ReportsPage() {
  return (
    <>
      <PageHeader title="Jelentések" subtitle="Készletérték és rendelési tevékenység áttekintése." />
      <div className="page-content">
        <StockValuationSection />
        <PurchaseActivitySection />
        <SalesFulfillmentActivitySection />
      </div>
    </>
  );
}

function StockValuationSection() {
  const [warehouseId, setWarehouseId] = useState<number | "">("");
  const [categoryId, setCategoryId] = useState<number | "">("");

  const warehousesQuery = useQuery({
    queryKey: ["warehouses", "for-select"],
    queryFn: () => warehousesApi.listWarehouses({ limit: 200 }),
  });
  const categoriesQuery = useQuery({
    queryKey: ["categories", "for-select"],
    queryFn: () => categoriesApi.listCategories({ limit: 200 }),
  });
  const warehouses = warehousesQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  const query = useQuery({
    queryKey: ["reports", "stock-valuation", { warehouseId, categoryId }],
    queryFn: () =>
      reportsApi.getStockValuation({ warehouse_id: warehouseId || undefined, category_id: categoryId || undefined }),
  });

  const warehouseColumns: Column<StockValuationByWarehouse>[] = [
    { key: "warehouse", header: "Raktár", render: (row) => row.warehouse.name },
    { key: "quantity", header: "Mennyiség", numeric: true, render: (row) => row.total_quantity },
    { key: "value", header: "Érték", numeric: true, render: (row) => formatAmount(row.total_value) },
  ];

  const categoryColumns: Column<StockValuationByCategory>[] = [
    { key: "category", header: "Kategória", render: (row) => row.category.name },
    { key: "quantity", header: "Mennyiség", numeric: true, render: (row) => row.total_quantity },
    { key: "value", header: "Érték", numeric: true, render: (row) => formatAmount(row.total_value) },
  ];

  return (
    <Panel>
      <div className="panel-header">
        <h3>Készletérték</h3>
      </div>
      <div className="filters-bar">
        <Field label="Raktár" htmlFor="rv-warehouse">
          <select
            id="rv-warehouse"
            value={warehouseId}
            onChange={(event) => setWarehouseId(event.target.value ? Number(event.target.value) : "")}
          >
            <option value="">Összes</option>
            {warehouses.map((warehouse) => (
              <option key={warehouse.id} value={warehouse.id}>
                {warehouse.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Kategória" htmlFor="rv-category">
          <select
            id="rv-category"
            value={categoryId}
            onChange={(event) => setCategoryId(event.target.value ? Number(event.target.value) : "")}
          >
            <option value="">Összes</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {query.data && (
        <div className="stat-grid" style={{ marginBottom: "1.2rem" }}>
          <Panel className="stat-tile">
            <div className="stat-label">Teljes mennyiség</div>
            <div className="stat-value">{query.data.total_quantity}</div>
          </Panel>
          <Panel className="stat-tile">
            <div className="stat-label">Teljes érték</div>
            <div className="stat-value">{formatAmount(query.data.total_value)}</div>
          </Panel>
        </div>
      )}

      <h4 className="text-dim" style={{ marginBottom: "0.6rem" }}>
        Raktáranként
      </h4>
      <DataTable
        columns={warehouseColumns}
        rows={query.data?.by_warehouse ?? []}
        rowKey={(row) => row.warehouse.id}
        isLoading={query.isLoading}
        emptyMessage={t.noResults}
      />

      <h4 className="text-dim" style={{ margin: "1.2rem 0 0.6rem" }}>
        Kategóriánként
      </h4>
      <DataTable
        columns={categoryColumns}
        rows={query.data?.by_category ?? []}
        rowKey={(row) => row.category.id}
        isLoading={query.isLoading}
        emptyMessage={t.noResults}
      />
    </Panel>
  );
}

function PurchaseActivitySection() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const query = useQuery({
    queryKey: ["reports", "purchase-activity", { dateFrom, dateTo }],
    queryFn: () => reportsApi.getPurchaseActivity({ date_from: dateFrom || undefined, date_to: dateTo || undefined }),
  });

  const columns: Column<PurchaseActivityRow>[] = [
    { key: "supplier", header: "Beszállító", render: (row) => row.supplier.name },
    { key: "submitted", header: "Beküldött rendelések", numeric: true, render: (row) => row.orders_submitted },
    { key: "received", header: "Átvett rendelések", numeric: true, render: (row) => row.orders_received },
    { key: "value", header: "Átvett érték", numeric: true, render: (row) => formatAmount(row.received_value) },
  ];

  return (
    <Panel>
      <div className="panel-header">
        <h3>Beszerzési tevékenység</h3>
      </div>
      <div className="filters-bar">
        <Field label="Kezdő dátum" htmlFor="pa-from">
          <input id="pa-from" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </Field>
        <Field label="Záró dátum" htmlFor="pa-to">
          <input id="pa-to" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </Field>
      </div>
      <DataTable
        columns={columns}
        rows={query.data ?? []}
        rowKey={(row) => row.supplier.id}
        isLoading={query.isLoading}
        emptyMessage={t.noResults}
      />
    </Panel>
  );
}

function SalesFulfillmentActivitySection() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const query = useQuery({
    queryKey: ["reports", "sales-fulfillment-activity", { dateFrom, dateTo }],
    queryFn: () =>
      reportsApi.getSalesFulfillmentActivity({ date_from: dateFrom || undefined, date_to: dateTo || undefined }),
  });

  const columns: Column<SalesFulfillmentActivityRow>[] = [
    { key: "customer", header: "Vevő", render: (row) => row.customer.name },
    { key: "confirmed", header: "Visszaigazolt rendelések", numeric: true, render: (row) => row.orders_confirmed },
    { key: "shipments", header: "Szállítmányok", numeric: true, render: (row) => row.shipments_created },
    { key: "value", header: "Szállított érték", numeric: true, render: (row) => formatAmount(row.shipped_value) },
  ];

  return (
    <Panel>
      <div className="panel-header">
        <h3>Értékesítési és teljesítési tevékenység</h3>
      </div>
      <div className="filters-bar">
        <Field label="Kezdő dátum" htmlFor="sf-from">
          <input id="sf-from" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </Field>
        <Field label="Záró dátum" htmlFor="sf-to">
          <input id="sf-to" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </Field>
      </div>
      <DataTable
        columns={columns}
        rows={query.data ?? []}
        rowKey={(row) => row.customer.id}
        isLoading={query.isLoading}
        emptyMessage={t.noResults}
      />
    </Panel>
  );
}
