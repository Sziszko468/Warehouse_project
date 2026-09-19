import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AlertIcon } from "./ui/icons";
import { GearSpinner } from "./ui/GearSpinner";

interface ProtectedRouteProps {
  children: ReactNode;
  adminOnly?: boolean;
}

export function ProtectedRoute({ children, adminOnly }: ProtectedRouteProps) {
  const { user, isLoading, isAdmin } = useAuth();

  if (isLoading) {
    return (
      <div className="auth-shell">
        <GearSpinner label="Betöltés…" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !isAdmin) {
    return (
      <div className="page-content">
        <div className="panel forbidden-panel">
          <AlertIcon />
          <h3>Nincs jogosultsága ehhez az oldalhoz</h3>
          <p className="text-dim">Ez a terület csak adminisztrátorok számára elérhető.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
