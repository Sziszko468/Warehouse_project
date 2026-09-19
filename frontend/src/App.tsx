import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { CategoriesPage } from "./pages/CategoriesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { MovementsPage } from "./pages/MovementsPage";
import { ProductsPage } from "./pages/ProductsPage";
import { RegisterPage } from "./pages/RegisterPage";
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
      <Route path="/warehouses" element={<ProtectedRoute>{withLayout(<WarehousesPage />)}</ProtectedRoute>} />
      <Route path="/stock" element={<ProtectedRoute>{withLayout(<StockPage />)}</ProtectedRoute>} />
      <Route path="/movements" element={<ProtectedRoute>{withLayout(<MovementsPage />)}</ProtectedRoute>} />
      <Route
        path="/users"
        element={
          <ProtectedRoute adminOnly>{withLayout(<UsersPage />)}</ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
