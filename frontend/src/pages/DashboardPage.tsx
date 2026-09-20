import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import * as productsApi from "../api/products";
import * as stockApi from "../api/stock";
import * as suppliersApi from "../api/suppliers";
import * as warehousesApi from "../api/warehouses";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge } from "../components/ui/Badge";
import { GearSpinner } from "../components/ui/GearSpinner";
import { AlertIcon, CrateIcon, TruckIcon, WarehouseIcon } from "../components/ui/icons";
import { Panel } from "../components/ui/Panel";
import { formatDateTime } from "../lib/format";
import { movementTypeLabels } from "../lib/movementLabels";

export function DashboardPage() {
  const productsQuery = useQuery({ queryKey: ["products", "dashboard-count"], queryFn: () => productsApi.listProducts({ limit: 1 }) });
  const warehousesQuery = useQuery({
    queryKey: ["warehouses", "dashboard-count"],
    queryFn: () => warehousesApi.listWarehouses({ limit: 1 }),
  });
  const suppliersQuery = useQuery({ queryKey: ["suppliers", "dashboard-count"], queryFn: () => suppliersApi.listSuppliers({ limit: 1 }) });
  const lowStockQuery = useQuery({ queryKey: ["stock", "low-stock", "dashboard"], queryFn: () => stockApi.listLowStock({ limit: 8 }) });
  const movementsQuery = useQuery({ queryKey: ["movements", "dashboard-recent"], queryFn: () => stockApi.listMovements({ limit: 8 }) });

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
      </div>
    </>
  );
}
