export type UserRole = "admin" | "staff";
export type MovementType = "in" | "out" | "transfer";
export type PurchaseOrderStatus = "draft" | "submitted" | "partially_received" | "received" | "cancelled";
export type CustomerOrderStatus = "draft" | "confirmed" | "partially_shipped" | "shipped" | "cancelled";
export type ShipmentStatus = "pending" | "in_transit" | "delivered" | "cancelled";

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

export interface Customer {
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

export interface SupplierBrief {
  id: number;
  name: string;
}

export interface CustomerBrief {
  id: number;
  name: string;
}

export interface CategoryBrief {
  id: number;
  name: string;
}

export interface Stock {
  id: number;
  product: ProductBrief;
  warehouse: WarehouseBrief;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
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

/** unit_price arrives as a JSON string (Decimal), never a number — parse with formatAmount(). */
export interface PurchaseOrderLine {
  id: number;
  product: ProductBrief;
  quantity_ordered: number;
  quantity_received: number;
  unit_price: string;
}

export interface PurchaseOrder {
  id: number;
  supplier: SupplierBrief;
  warehouse: WarehouseBrief;
  status: PurchaseOrderStatus;
  notes: string | null;
  created_by: UserBrief;
  lines: PurchaseOrderLine[];
  submitted_at: string | null;
  received_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerOrderLine {
  id: number;
  product: ProductBrief;
  quantity_ordered: number;
  quantity_shipped: number;
  unit_price: string;
}

export interface CustomerOrder {
  id: number;
  customer: CustomerBrief;
  warehouse: WarehouseBrief;
  status: CustomerOrderStatus;
  notes: string | null;
  created_by: UserBrief;
  lines: CustomerOrderLine[];
  confirmed_at: string | null;
  shipped_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShipmentLine {
  id: number;
  product: ProductBrief;
  quantity: number;
}

export type AuditAction = "create" | "update" | "status_change" | "soft_delete";

export interface AuditLog {
  id: number;
  entity_type: string;
  entity_id: number;
  action: AuditAction;
  performed_by: UserBrief;
  summary: string | null;
  changes: Record<string, { old: string; new: string }> | null;
  created_at: string;
}

export interface Shipment {
  id: number;
  customer_order_id: number;
  carrier: string | null;
  tracking_number: string | null;
  status: ShipmentStatus;
  lines: ShipmentLine[];
  shipped_at: string | null;
  delivered_at: string | null;
  created_by: UserBrief;
  created_at: string;
  updated_at: string;
}
