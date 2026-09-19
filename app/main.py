from fastapi import FastAPI

app = FastAPI(
    title="StockFlow",
    description="Warehouse Management System REST API",
    version="0.1.0",
)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}
