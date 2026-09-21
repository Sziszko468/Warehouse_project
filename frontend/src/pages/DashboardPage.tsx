import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import * as auditLogsApi from "../api/auditLogs";
import * as customerOrdersApi from "../api/customerOrders";
import * as productsApi from "../api/products";
import * as purchaseOrdersApi from "../api/purchaseOrders";
import * as shipmentsApi from "../api/shipments";
import * as stockApi from "../api/stock";
import * as suppliersApi from "../api/suppliers";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { GearSpinner } from "../components/ui/GearSpinner";
import {
  AlertIcon,
  CartIcon,
  ClipboardIcon,
  CrateIcon,
  ShipmentIcon,
  TruckIcon,
  WarehouseIcon,
} from "../components/ui/icons";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/useAuth";
import { formatDateTime } from "../lib/format";
import { movementTypeLabels } from "../lib/movementLabels";
import type { AuditLog } from "../types";

const ACTIVITY_ENTITY_TYPES = ["PurchaseOrder", "CustomerOrder", "Shipment"] as const;

export function DashboardPage() {
  const { isAdmin } = useAuth();

  const productsQuery = useQuery({ queryKey: ["products", "dashboard-count"], queryFn: () => productsApi.listProducts({ limit: 1 }) });
  const warehousesQuery = useQuery({
    queryKey: ["warehouses", "dashboard-count"],
    queryFn: () => warehousesApi.listWarehouses({ limit: 1 }),
  });
  const suppliersQuery = useQuery({ queryKey: ["suppliers", "dashboard-count"], queryFn: () => suppliersApi.listSuppliers({ limit: 1 }) });
  const lowStockQuery = useQuery({ queryKey: ["stock", "low-stock", "dashboard"], queryFn: () => stockApi.listLowStock({ limit: 8 }) });
  const movementsQuery = useQuery({ queryKey: ["movements", "dashboard-recent"], queryFn: () => stockApi.listMovements({ limit: 8 }) });

  const submittedPOsQuery = useQuery({
    queryKey: ["purchase-orders", "dashboard-count", "submitted"],
    queryFn: () => purchaseOrdersApi.listPurchaseOrders({ status: "submitted", limit: 1 }),
  });
  const partiallyReceivedPOsQuery = useQuery({
    queryKey: ["purchase-orders", "dashboard-count", "partially_received"],
    queryFn: () => purchaseOrdersApi.listPurchaseOrders({ status: "partially_received", limit: 1 }),
  });
  const openPurchaseOrders = (submittedPOsQuery.data?.total ?? 0) + (partiallyReceivedPOsQuery.data?.total ?? 0);

  const confirmedCOsQuery = useQuery({
    queryKey: ["customer-orders", "dashboard-count", "confirmed"],
    queryFn: () => customerOrdersApi.listCustomerOrders({ status: "confirmed", limit: 1 }),
  });
  const partiallyShippedCOsQuery = useQuery({
    queryKey: ["customer-orders", "dashboard-count", "partially_shipped"],
    queryFn: () => customerOrdersApi.listCustomerOrders({ status: "partially_shipped", limit: 1 }),
  });
  const openCustomerOrders = (confirmedCOsQuery.data?.total ?? 0) + (partiallyShippedCOsQuery.data?.total ?? 0);

  const pendingShipmentsQuery = useQuery({
    queryKey: ["shipments", "dashboard-count", "pending"],
    queryFn: () => shipmentsApi.listShipments({ status: "pending", limit: 1 }),
  });
  const inTransitShipmentsQuery = useQuery({
    queryKey: ["shipments", "dashboard-count", "in_transit"],
    queryFn: () => shipmentsApi.listShipments({ status: "in_transit", limit: 1 }),
  });
  const pendingShipments = (pendingShipmentsQuery.data?.total ?? 0) + (inTransitShipmentsQuery.data?.total ?? 0);

  // /audit-logs is admin-only - only fire these queries (and render the panel) for admins, since
  // a staff session would just get a 403 back.
  const activityQueries = useQuery({
    queryKey: ["audit-logs", "dashboard-recent"],
    enabled: isAdmin,
    queryFn: async () => {
      const results = await Promise.all(
        ACTIVITY_ENTITY_TYPES.map((entity_type) => auditLogsApi.listAuditLogs({ entity_type, limit: 8 })),
      );
      const merged: AuditLog[] = results.flatMap((page) => page.items);
      merged.sort((a, b) => b.created_at.localeCompare(a.created_at));
      return merged.slice(0, 8);
    },
  });

  return (
    <>
      <PageHeader title="Irányítópult" subtitle="A raktár állapotának áttekintése egy pillantással." />
      <div className="page-content">
        <div className="stat-grid">
          <Panel className="stat-tile">
            <div className="stat-label">
              <CrateIcon />
              Termékek
            </div>
            <div className="stat-value">{productsQuery.data?.total ?? "…"}</div>
          </Panel>
          <Panel className="stat-tile">
            <div className="stat-label">
              <WarehouseIcon />
              Raktárak
            </div>
            <div className="stat-value">{warehousesQuery.data?.total ?? "…"}</div>
          </Panel>
          <Panel className="stat-tile">
            <div className="stat-label">
              <TruckIcon />
              Beszállítók
            </div>
            <div className="stat-value">{suppliersQuery.data?.total ?? "…"}</div>
          </Panel>
          <Panel className="stat-tile">
            <div className="stat-label">
              <AlertIcon />
              Alacsony készlet
            </div>
            <div className="stat-value">{lowStockQuery.data?.total ?? "…"}</div>
          </Panel>
          <Panel className="stat-tile">
            <div className="stat-label">
              <ClipboardIcon />
              Nyitott beszerzési rendelések
            </div>
            <div className="stat-value">
              {submittedPOsQuery.isLoading || partiallyReceivedPOsQuery.isLoading ? "…" : openPurchaseOrders}
            </div>
          </Panel>
          <Panel className="stat-tile">
            <div className="stat-label">
              <CartIcon />
              Nyitott vevői rendelések
            </div>
            <div className="stat-value">
              {confirmedCOsQuery.isLoading || partiallyShippedCOsQuery.isLoading ? "…" : openCustomerOrders}
            </div>
          </Panel>
          <Panel className="stat-tile">
            <div className="stat-label">
              <ShipmentIcon />
              Folyamatban lévő szállítmányok
            </div>
            <div className="stat-value">
              {pendingShipmentsQuery.isLoading || inTransitShipmentsQuery.isLoading ? "…" : pendingShipments}
            </div>
          </Panel>
        </div>

        <Panel>
          <div className="panel-header">
            <h3>
              <AlertIcon style={{ verticalAlign: "-3px", marginRight: "0.5rem", color: "var(--spf-danger-bright)" }} />
              Alacsony készletű tételek
            </h3>
            <Link to="/stock" className="text-dim">
              Összes készlet →
            </Link>
          </div>
          {lowStockQuery.isLoading ? (
            <GearSpinner label="Betöltés…" />
          ) : lowStockQuery.data && lowStockQuery.data.items.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Termék</th>
                    <th>Raktár</th>
                    <th className="num">Készlet</th>
                    <th className="num">Minimum</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStockQuery.data.items.map((row) => (
                    <tr key={row.id}>
                      <td>
                        {row.product.name} <span className="text-faint mono">{row.product.sku}</span>
                      </td>
                      <td>{row.warehouse.name}</td>
                      <td className="num">
                        <Badge kind="danger">{row.quantity}</Badge>
                      </td>
                      <td className="num text-dim">{row.min_stock_threshold}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">Minden tétel készlete megfelelő szinten van.</div>
          )}
        </Panel>

        <Panel>
          <div className="panel-header">
            <h3>Legutóbbi készletmozgások</h3>
            <Link to="/movements" className="text-dim">
              Teljes napló →
            </Link>
          </div>
          {movementsQuery.isLoading ? (
            <GearSpinner label="Betöltés…" />
          ) : movementsQuery.data && movementsQuery.data.items.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Időpont</th>
                    <th>Termék</th>
                    <th>Típus</th>
                    <th className="num">Mennyiség</th>
                  </tr>
                </thead>
                <tbody>
                  {movementsQuery.data.items.map((row) => (
                    <tr key={row.id}>
                      <td>{formatDateTime(row.created_at)}</td>
                      <td>{row.product.name}</td>
                      <td>{movementTypeLabels[row.movement_type]}</td>
                      <td className="num">{row.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">Még nem történt készletmozgás.</div>
          )}
        </Panel>

        {isAdmin && (
          <Panel>
            <div className="panel-header">
              <h3>Legutóbbi rendelési tevékenység</h3>
              <Link to="/audit-log" className="text-dim">
                Teljes audit napló →
              </Link>
            </div>
            {activityQueries.isLoading ? (
              <GearSpinner label="Betöltés…" />
            ) : activityQueries.data && activityQueries.data.length > 0 ? (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Időpont</th>
                      <th>Erőforrás</th>
                      <th>Művelet</th>
                      <th>Végrehajtó</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activityQueries.data.map((row) => (
                      <tr key={row.id}>
                        <td>{formatDateTime(row.created_at)}</td>
                        <td>
                          {row.entity_type} #{row.entity_id}
                        </td>
                        <td>{row.summary ?? row.action}</td>
                        <td>{row.performed_by.full_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">Még nem történt rendelési tevékenység.</div>
            )}
          </Panel>
        )}
      </div>
    </>
  );
}
