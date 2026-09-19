export type UserRole = "admin" | "staff";
export type MovementType = "in" | "out" | "transfer";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface Supplier {
  id: number;
  name: string;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  is_active: boolean;
}

export interface Warehouse {
  id: number;
  name: string;
  address: string | null;
  is_active: boolean;
}

/** unit_price arrives as a JSON string (Decimal), never a number — parse with parseAmount(). */
export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  category_id: number;
  supplier_id: number | null;
  unit_price: string;
  min_stock_threshold: number;
  is_active: boolean;
}

export interface ProductBrief {
  id: number;
  sku: string;
  name: string;
}

export interface WarehouseBrief {
  id: number;
  name: string;
}

export interface UserBrief {
  id: number;
  email: string;
  full_name: string;
}

export interface Stock {
  id: number;
  product: ProductBrief;
  warehouse: WarehouseBrief;
  quantity: number;
  updated_at: string;
}

export interface LowStock extends Stock {
  min_stock_threshold: number;
}

export interface StockMovement {
  id: number;
  product: ProductBrief;
  movement_type: MovementType;
  quantity: number;
  from_warehouse: WarehouseBrief | null;
  to_warehouse: WarehouseBrief | null;
  note: string | null;
  performed_by: UserBrief;
  created_at: string;
}
