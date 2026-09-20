import { ApiError } from "../api/client";

// The backend's error `detail` strings are in English (a REST API concern, not a UI concern).
// This translates the known ones for the Hungarian UI; anything unrecognized (e.g. a 422
// validation message we haven't special-cased) is shown as-is rather than hidden.
const EXACT_TRANSLATIONS: Record<string, string> = {
  "Product not found": "A termék nem található.",
  "Warehouse not found": "A raktár nem található.",
  "Category not found": "A kategória nem található.",
  "Supplier not found": "A beszállító nem található.",
  "User not found": "A felhasználó nem található.",
  "Resource not found": "Az erőforrás nem található.",
  "Email already registered": "Ez az e-mail cím már regisztrálva van.",
  "Category name already exists": "Ez a kategórianév már létezik.",
  "Warehouse name already exists": "Ez a raktárnév már létezik.",
  "SKU already exists": "Ez a cikkszám már létezik.",
  "Incorrect email or password": "Hibás e-mail cím vagy jelszó.",
  "Could not validate credentials": "A hitelesítés nem sikerült. Jelentkezzen be újra.",
  "Admin privileges required": "Ehhez a művelethez adminisztrátori jogosultság szükséges.",
  "Cannot transfer stock to the same warehouse": "Nem lehet ugyanabba a raktárba áthelyezni a készletet.",
  "Cannot demote or deactivate the last active admin":
    "Az utolsó aktív adminisztrátor jogosultsága nem vonható vissza, és nem tiltható le.",
  "Request conflicts with existing data": "A kérés ütközik egy meglévő adattal.",
  "Customer not found": "A vevő nem található.",
  "Purchase order not found": "A beszerzési rendelés nem található.",
  "Purchase order line not found on this order": "A tétel nem tartozik ehhez a beszerzési rendeléshez.",
  "Purchase order is not in draft status": "A beszerzési rendelés nincs piszkozat állapotban.",
  "Purchase order is not submitted or partially received": "A rendelés nincs beküldve vagy részben átvéve állapotban.",
  "Purchase order cannot be cancelled once receiving has started":
    "A rendelés nem törölhető, miután az átvétel elkezdődött.",
  "Customer order not found": "A vevői rendelés nem található.",
  "Customer order line not found on this order": "A tétel nem tartozik ehhez a vevői rendeléshez.",
  "Customer order is not in draft status": "A vevői rendelés nincs piszkozat állapotban.",
  "Customer order cannot be cancelled once shipping has started":
    "A rendelés nem törölhető, miután a szállítás elkezdődött.",
  "Shipment not found": "A szállítmány nem található.",
  "Order line does not belong to this shipment's customer order": "A tétel nem tartozik ehhez a rendeléshez.",
  "Customer order is not confirmed or partially shipped": "A rendelés nincs visszaigazolva vagy részben szállítva állapotban.",
  "Shipment is not pending": "A szállítmány nincs függőben állapotban.",
  "Shipment is not in transit": "A szállítmány nincs szállítás alatt állapotban.",
  "Shipment cannot be cancelled once delivered": "A kiszállított szállítmány nem törölhető.",
};

const INSUFFICIENT_STOCK = /^Insufficient stock: requested (\d+), available (\d+)$/;
const OVER_RECEIPT = /^Cannot receive (\d+) units: only (\d+) remain on this order line$/;
const OVER_SHIPMENT = /^Cannot ship (\d+) units: only (\d+) remain unshipped on this order line$/;

function translate(detail: string): string {
  const exact = EXACT_TRANSLATIONS[detail];
  if (exact) return exact;

  const stockMatch = detail.match(INSUFFICIENT_STOCK);
  if (stockMatch) {
    const [, requested, available] = stockMatch;
    return `Nincs elég készlet: kért mennyiség ${requested}, elérhető ${available}.`;
  }

  const overReceiptMatch = detail.match(OVER_RECEIPT);
  if (overReceiptMatch) {
    const [, requested, remaining] = overReceiptMatch;
    return `${requested} db nem vehető át: a tételből csak ${remaining} db van hátra.`;
  }

  const overShipmentMatch = detail.match(OVER_SHIPMENT);
  if (overShipmentMatch) {
    const [, requested, remaining] = overShipmentMatch;
    return `${requested} db nem szállítható: a tételből csak ${remaining} db van hátra.`;
  }

  return detail;
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return translate(error.detail);
  if (error instanceof Error) return error.message;
  return "Váratlan hiba történt.";
}
