"""Every HTTP error `detail` string the API returns, centralized in one place.

Both the app (routers/services/exceptions) and the test suite import from here instead of typing
the text out a second time - a test can never silently drift from what the API actually says, and
swapping to a different language (or wiring up real i18n) later is a one-file change.
"""


class Messages:
    # auth / dependencies
    COULD_NOT_VALIDATE_CREDENTIALS = "Could not validate credentials"
    ADMIN_PRIVILEGES_REQUIRED = "Admin privileges required"
    EMAIL_ALREADY_REGISTERED = "Email already registered"
    INCORRECT_CREDENTIALS = "Incorrect email or password"

    # categories
    CATEGORY_NOT_FOUND = "Category not found"
    CATEGORY_NAME_EXISTS = "Category name already exists"

    # suppliers
    SUPPLIER_NOT_FOUND = "Supplier not found"

    # customers
    CUSTOMER_NOT_FOUND = "Customer not found"

    # warehouses
    WAREHOUSE_NOT_FOUND = "Warehouse not found"
    WAREHOUSE_NAME_EXISTS = "Warehouse name already exists"

    # products
    PRODUCT_NOT_FOUND = "Product not found"
    SKU_ALREADY_EXISTS = "SKU already exists"

    # users
    USER_NOT_FOUND = "User not found"
    LAST_ADMIN_GUARD = "Cannot demote or deactivate the last active admin"

    # stock
    SELF_TRANSFER_REJECTED = "Cannot transfer stock to the same warehouse"
    INSUFFICIENT_STOCK_DEFAULT = "Insufficient stock for this operation"

    # purchase orders
    PURCHASE_ORDER_NOT_FOUND = "Purchase order not found"
    PURCHASE_ORDER_LINE_NOT_FOUND = "Purchase order line not found on this order"
    PURCHASE_ORDER_NOT_DRAFT = "Purchase order is not in draft status"
    PURCHASE_ORDER_NOT_RECEIVABLE = "Purchase order is not submitted or partially received"
    PURCHASE_ORDER_CANNOT_CANCEL = "Purchase order cannot be cancelled once receiving has started"

    # customer orders
    CUSTOMER_ORDER_NOT_FOUND = "Customer order not found"
    CUSTOMER_ORDER_LINE_NOT_FOUND = "Customer order line not found on this order"
    CUSTOMER_ORDER_NOT_DRAFT = "Customer order is not in draft status"
    CUSTOMER_ORDER_CANNOT_CANCEL = "Customer order cannot be cancelled once shipping has started"

    # shipments
    SHIPMENT_NOT_FOUND = "Shipment not found"
    SHIPMENT_LINE_NOT_ON_ORDER = "Order line does not belong to this shipment's customer order"
    SHIPMENT_ORDER_NOT_SHIPPABLE = "Customer order is not confirmed or partially shipped"
    SHIPMENT_NOT_PENDING = "Shipment is not pending"
    SHIPMENT_NOT_IN_TRANSIT = "Shipment is not in transit"
    SHIPMENT_CANNOT_CANCEL = "Shipment cannot be cancelled once delivered"

    # audit log
    AUDIT_LOG_NOT_FOUND = "Audit log entry not found"

    # generic fallbacks (exception class defaults - callers normally pass a specific message above)
    RESOURCE_NOT_FOUND = "Resource not found"
    CONFLICTS_WITH_EXISTING_DATA = "Request conflicts with existing data"

    @staticmethod
    def insufficient_stock(requested: int, available: int) -> str:
        return f"Insufficient stock: requested {requested}, available {available}"

    @staticmethod
    def over_receipt(requested: int, remaining: int) -> str:
        return f"Cannot receive {requested} units: only {remaining} remain on this order line"

    @staticmethod
    def over_shipment(requested: int, remaining: int) -> str:
        return f"Cannot ship {requested} units: only {remaining} remain unshipped on this order line"


class NotificationMessages:
    """Every Celery background-job notification's subject/body, centralized in one place - same
    reasoning as Messages above: keeps templates from drifting across call sites, and keeps
    swapping to a different language a one-file change.
    """

    @staticmethod
    def purchase_order_submitted(*, purchase_order_id: int, supplier_name: str) -> tuple[str, str]:
        return (
            f"PO-{purchase_order_id} submitted",
            f"Purchase order PO-{purchase_order_id} to {supplier_name} has been submitted.",
        )

    @staticmethod
    def purchase_order_received(*, purchase_order_id: int, supplier_name: str) -> tuple[str, str]:
        return (
            f"PO-{purchase_order_id} received in full",
            f"Purchase order PO-{purchase_order_id} from {supplier_name} has been fully received.",
        )

    @staticmethod
    def customer_order_shipped(*, customer_order_id: int, customer_name: str) -> tuple[str, str]:
        return (
            f"CO-{customer_order_id} fully shipped",
            f"Customer order CO-{customer_order_id} for {customer_name} has been fully shipped.",
        )

    @staticmethod
    def low_stock(*, product_name: str, warehouse_name: str, quantity: int, threshold: int) -> tuple[str, str]:
        return (
            f"Low stock: {product_name} at {warehouse_name}",
            f"{product_name} at {warehouse_name} has dropped to {quantity} units, "
            f"at or below the minimum threshold of {threshold}.",
        )

    @staticmethod
    def stock_report(*, report_date: str) -> str:
        return f"Scheduled stock report - {report_date}"
