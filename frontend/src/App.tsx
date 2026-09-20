import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuditLogPage } from "./pages/AuditLogPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { CustomerOrdersPage } from "./pages/CustomerOrdersPage";
import { CustomersPage } from "./pages/CustomersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { MovementsPage } from "./pages/MovementsPage";
import { ProductsPage } from "./pages/ProductsPage";
import { PurchaseOrdersPage } from "./pages/PurchaseOrdersPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ReportsPage } from "./pages/ReportsPage";
import { ShipmentsPage } from "./pages/ShipmentsPage";
import { StockPage } from "./pages/StockPage";
import { SuppliersPage } from "./pages/SuppliersPage";
import { UsersPage } from "./pages/UsersPage";
import { WarehousesPage } from "./pages/WarehousesPage";

function withLayout(children: ReactNode) {
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route path="/" element={<ProtectedRoute>{withLayout(<DashboardPage />)}</ProtectedRoute>} />
      <Route path="/products" element={<ProtectedRoute>{withLayout(<ProductsPage />)}</ProtectedRoute>} />
      <Route path="/categories" element={<ProtectedRoute>{withLayout(<CategoriesPage />)}</ProtectedRoute>} />
      <Route path="/suppliers" element={<ProtectedRoute>{withLayout(<SuppliersPage />)}</ProtectedRoute>} />
      <Route path="/customers" element={<ProtectedRoute>{withLayout(<CustomersPage />)}</ProtectedRoute>} />
      <Route path="/warehouses" element={<ProtectedRoute>{withLayout(<WarehousesPage />)}</ProtectedRoute>} />
      <Route path="/stock" element={<ProtectedRoute>{withLayout(<StockPage />)}</ProtectedRoute>} />
      <Route path="/movements" element={<ProtectedRoute>{withLayout(<MovementsPage />)}</ProtectedRoute>} />
      <Route path="/purchase-orders" element={<ProtectedRoute>{withLayout(<PurchaseOrdersPage />)}</ProtectedRoute>} />
      <Route path="/customer-orders" element={<ProtectedRoute>{withLayout(<CustomerOrdersPage />)}</ProtectedRoute>} />
      <Route path="/shipments" element={<ProtectedRoute>{withLayout(<ShipmentsPage />)}</ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute>{withLayout(<ReportsPage />)}</ProtectedRoute>} />
      <Route
        path="/users"
        element={
          <ProtectedRoute adminOnly>{withLayout(<UsersPage />)}</ProtectedRoute>
        }
      />
      <Route
        path="/audit-log"
        element={
          <ProtectedRoute adminOnly>{withLayout(<AuditLogPage />)}</ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
