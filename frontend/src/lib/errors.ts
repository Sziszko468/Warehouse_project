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
};

const INSUFFICIENT_STOCK = /^Insufficient stock: requested (\d+), available (\d+)$/;

function translate(detail: string): string {
  const exact = EXACT_TRANSLATIONS[detail];
  if (exact) return exact;

  const stockMatch = detail.match(INSUFFICIENT_STOCK);
  if (stockMatch) {
    const [, requested, available] = stockMatch;
    return `Nincs elég készlet: kért mennyiség ${requested}, elérhető ${available}.`;
  }

  return detail;
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return translate(error.detail);
  if (error instanceof Error) return error.message;
  return "Váratlan hiba történt.";
}
