const amountFormatter = new Intl.NumberFormat("hu-HU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dateTimeFormatter = new Intl.DateTimeFormat("hu-HU", { dateStyle: "medium", timeStyle: "short" });

/** unit_price arrives from the API as a Decimal-string, e.g. "4.99". */
export function formatAmount(value: string): string {
  const num = Number.parseFloat(value);
  return Number.isFinite(num) ? amountFormatter.format(num) : value;
}

export function formatDateTime(isoString: string): string {
  return dateTimeFormatter.format(new Date(isoString));
}
