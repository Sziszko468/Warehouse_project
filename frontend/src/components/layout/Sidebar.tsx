import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import {
  CrateIcon,
  DashboardIcon,
  GearIcon,
  LayersIcon,
  LedgerIcon,
  LogoutIcon,
  TagIcon,
  TruckIcon,
  UsersIcon,
  WarehouseIcon,
} from "../ui/icons";

const navItems = [
  { to: "/", label: "Irányítópult", icon: DashboardIcon, end: true },
  { to: "/products", label: "Termékek", icon: CrateIcon, end: false },
  { to: "/categories", label: "Kategóriák", icon: TagIcon, end: false },
  { to: "/suppliers", label: "Beszállítók", icon: TruckIcon, end: false },
  { to: "/warehouses", label: "Raktárak", icon: WarehouseIcon, end: false },
  { to: "/stock", label: "Készlet", icon: LayersIcon, end: false },
  { to: "/movements", label: "Mozgási napló", icon: LedgerIcon, end: false },
];

export function Sidebar() {
  const { user, isAdmin, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <GearIcon className="gear-icon" />
        <div className="sidebar-brand-text">
          <h1>StockFlow</h1>
          <small>Raktárkezelő Rendszer</small>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
            <Icon />
            <span className="label">{label}</span>
          </NavLink>
        ))}
        {isAdmin && (
          <NavLink to="/users" className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
            <UsersIcon />
            <span className="label">Felhasználók</span>
          </NavLink>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <span className="sidebar-user-name">{user?.full_name}</span>
          <Badge kind={isAdmin ? "admin" : "staff"}>{isAdmin ? "Admin" : "Munkatárs"}</Badge>
        </div>
        <Button variant="ghost" size="sm" onClick={logout} style={{ width: "100%" }}>
          <LogoutIcon />
          <span className="label">Kijelentkezés</span>
        </Button>
      </div>
    </aside>
  );
}
