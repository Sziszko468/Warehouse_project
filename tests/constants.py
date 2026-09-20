"""Shared numeric/string values for tests, so a scenario number isn't a magic literal sprinkled
across dozens of test files - change a value once here rather than hunting through every test.
"""

# stock quantities
DEFAULT_QUANTITY = 100
SMALL_QUANTITY = 10
LARGE_QUANTITY = 50
EXCESS_QUANTITY = 999_999  # deliberately more than any test ever stocks, to force insufficient-stock

# thresholds
LOW_STOCK_THRESHOLD = 5
ZERO_THRESHOLD = 0

# pagination - mirrors app.dependencies.PaginationParams' own bounds
PAGE_LIMIT_DEFAULT = 50
PAGE_LIMIT_MAX = 200
PAGE_LIMIT_SMALL = 2  # small enough that a handful of rows spans multiple pages

# money
SAMPLE_UNIT_PRICE = "9.99"
ALTERNATE_UNIT_PRICE = "19.99"

# auth
SAMPLE_PASSWORD = "correct-horse-battery"
MIN_PASSWORD_LENGTH = 8  # matches RegisterPage's client-side minLength; backend itself is unbound
