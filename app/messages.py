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

    # generic fallbacks (exception class defaults - callers normally pass a specific message above)
    RESOURCE_NOT_FOUND = "Resource not found"
    CONFLICTS_WITH_EXISTING_DATA = "Request conflicts with existing data"

    @staticmethod
    def insufficient_stock(requested: int, available: int) -> str:
        return f"Insufficient stock: requested {requested}, available {available}"
